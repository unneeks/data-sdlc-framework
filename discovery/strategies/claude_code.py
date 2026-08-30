"""Claude Code strategy — Claude Code itself walks the repo.

Unlike other strategies, this one doesn't call itself via an API.
Claude Code has native file access (Read, Bash), git awareness, and
can reason across files. The "implementation" is the skill instructions
that guide Claude Code's behavior.

This class provides:
  1. The skill loader (what instructions to follow)
  2. A programmatic fallback (run tools directly when invoked from Python)
  3. A report builder

In practice, Claude Code discovery is invoked by:
  - Asking Claude Code to run /discover
  - A background fork that walks the repo
  - The API triggering a claude-code-batch mode
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from discovery.result import (
    DiscoveredEntity,
    DiscoveredRelationship,
    DiscoveryReport,
    DiscoverySkip,
    DiscoveryFailure,
)
from discovery.strategy import DiscoveryConfig
from discovery.tools.walk import walk_repository, SOURCE_KIND_ENTITY_TYPES
from discovery.tools.read import read_file
from discovery.tools.deep_walk import deep_walk_repository
from discovery.tools.resolve import resolve_relationships
from discovery.tools.ingest import ingest_entities, ingest_relationships


def _load_skill(skill_name: str) -> str:
    """Load skill instructions for Claude Code to follow."""
    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    skill_path = skills_dir / f"{skill_name}.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")
    return skill_path.read_text(encoding="utf-8")


class ClaudeCodeStrategy:
    """Claude Code walks the repo using its native tools.

    Two modes:
      - "interactive": Claude Code reads files, reasons, and asks user
        about ambiguities. Best for initial discovery.
      - "batch": Runs programmatically without interaction. Uses the
        walk tool + simple heuristic extraction (no LLM for extraction,
        relies on structural patterns like dbt ref(), Terraform resource
        blocks, etc).
    """

    name = "claude-code"

    def __init__(self, *, mode: str = "batch"):
        self._mode = mode

    @property
    def skill_instructions(self) -> str:
        """Get the skill instructions Claude Code should follow.

        In interactive mode, Claude Code reads these and follows them.
        In batch mode, the discover() method implements them directly.
        """
        return _load_skill("repository-discovery")

    def discover(self, config: DiscoveryConfig) -> DiscoveryReport:
        """Batch-mode discovery using structural heuristics.

        No LLM calls for extraction — uses pattern matching on file
        content to extract entities. Suitable for dbt projects, Terraform,
        Airflow DAGs, and CI/CD workflows where structure is predictable.
        """
        walk_result = walk_repository(
            str(config.repository_root),
            extra_exclude_dirs=list(config.extra_exclude_dirs),
        )

        all_entities: list[DiscoveredEntity] = []
        all_rel_candidates: list[dict[str, Any]] = []
        skipped: list[DiscoverySkip] = []
        failed: list[DiscoveryFailure] = []

        # Technical files — structural extraction
        for candidate in walk_result["technical"]:
            file_result = read_file(str(config.repository_root), candidate["path"])
            if "error" in file_result:
                skipped.append(DiscoverySkip(
                    kind=file_result["error"],
                    detail=str(file_result.get("size", "")),
                    source=candidate["path"],
                ))
                continue

            entities, rels = self._extract_structural(
                candidate["path"],
                file_result["content"],
                candidate["source_kind"],
                config.project_id,
            )
            all_entities.extend(entities)
            all_rel_candidates.extend(rels)

        # Delivery files — lightweight heading extraction
        for candidate in walk_result["delivery"]:
            file_result = read_file(str(config.repository_root), candidate["path"])
            if "error" in file_result:
                skipped.append(DiscoverySkip(
                    kind=file_result["error"],
                    detail=str(file_result.get("size", "")),
                    source=candidate["path"],
                ))
                continue

            entities, rels = self._extract_delivery_structural(
                candidate["path"],
                file_result["content"],
                config.project_id,
            )
            all_entities.extend(entities)
            all_rel_candidates.extend(rels)

        # Deep walk for module structure, patterns, SBOM, responsibilities
        deep_report = deep_walk_repository(
            str(config.repository_root),
            extra_exclude_dirs=list(config.extra_exclude_dirs),
        )

        # Resolve + Ingest
        resolution = resolve_relationships(all_rel_candidates, all_entities)
        skipped.extend(
            DiscoverySkip(kind=s["kind"], detail=s["detail"], source=s["source"])
            for s in resolution["skipped_details"]
        )

        ingest_result = ingest_entities(
            config.project_id,
            [
                {
                    "entity_type": e.entity_type,
                    "name": e.name,
                    "entity_id": e.entity_id,
                    "source_document": e.source_document,
                    "provenance": e.provenance,
                    "confidence": e.confidence,
                    "attributes": e.attributes,
                }
                for e in all_entities
            ],
        )
        rel_ingest = ingest_relationships(config.project_id, resolution["relationships"])

        by_type: dict[str, int] = {}
        for e in all_entities:
            by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1

        return DiscoveryReport(
            project_id=config.project_id,
            strategy=f"{self.name}-{self._mode}",
            skill=config.skill,
            entities_discovered=ingest_result["ingested"],
            relationships_discovered=rel_ingest["ingested"],
            entities_by_type=by_type,
            entities=all_entities,
            relationships=[DiscoveredRelationship(**r) for r in resolution["relationships"]],
            skipped=skipped,
            failed=failed,
            deep_analysis=deep_report if "error" not in deep_report else None,
        )

    def _extract_structural(
        self, path: str, content: str, source_kind: str, project_id: str,
    ) -> tuple[list[DiscoveredEntity], list[dict[str, Any]]]:
        """Extract entities from technical files using structural patterns."""
        entities: list[DiscoveredEntity] = []
        relationships: list[dict[str, Any]] = []

        if source_kind == "sql":
            entities, relationships = self._extract_sql(path, content)
        elif source_kind == "terraform":
            entities, relationships = self._extract_terraform(path, content)
        elif source_kind == "python":
            entities, relationships = self._extract_python(path, content)
        elif source_kind in ("dockerfile", "compose"):
            entities = self._extract_infra(path, content, source_kind)
        elif source_kind == "ci_workflow":
            entities = self._extract_ci(path, content)
        elif source_kind == "yaml_config":
            entities = self._extract_yaml_config(path, content)
        elif source_kind == "json_config":
            entities = self._extract_json_config(path, content)

        return entities, relationships

    def _extract_sql(self, path: str, content: str) -> tuple[list[DiscoveredEntity], list[dict]]:
        """Extract from SQL/dbt models: refs, sources, model name."""
        import re

        name = Path(path).stem
        entities = [DiscoveredEntity(
            entity_type="Pipeline",
            entity_id=f"pipeline:{name}",
            name=name,
            source_document=path,
            provenance="OBSERVED",
            confidence=1.0,
            attributes={"pipeline_kind": "dbt_model", "source_path": path},
        )]

        relationships = []
        # dbt ref() dependencies
        for match in re.finditer(r"\{\{\s*ref\(['\"](\w+)['\"]\)\s*\}\}", content):
            dep = match.group(1)
            relationships.append({
                "relationship_type": "DEPENDS_ON",
                "source": name,
                "target": dep,
                "confidence": 1.0,
                "source_document": path,
            })

        # dbt source() references
        for match in re.finditer(r"\{\{\s*source\(['\"](\w+)['\"],\s*['\"](\w+)['\"]\)\s*\}\}", content):
            schema, table = match.group(1), match.group(2)
            asset_name = f"{schema}.{table}"
            entities.append(DiscoveredEntity(
                entity_type="DataAsset",
                entity_id=f"dataasset:{schema}_{table}",
                name=asset_name,
                source_document=path,
                provenance="OBSERVED",
                confidence=1.0,
                attributes={"asset_kind": "source_table", "schema_name": schema},
            ))
            relationships.append({
                "relationship_type": "DEPENDS_ON",
                "source": name,
                "target": asset_name,
                "confidence": 1.0,
                "source_document": path,
            })

        return entities, relationships

    def _extract_terraform(self, path: str, content: str) -> tuple[list[DiscoveredEntity], list[dict]]:
        """Extract Terraform resources and modules."""
        import re

        entities = []
        relationships = []

        for match in re.finditer(r'resource\s+"(\w+)"\s+"(\w+)"', content):
            resource_type, resource_name = match.group(1), match.group(2)
            entities.append(DiscoveredEntity(
                entity_type="Infrastructure",
                entity_id=f"infra:{resource_type}_{resource_name}",
                name=f"{resource_type}.{resource_name}",
                source_document=path,
                provenance="OBSERVED",
                confidence=1.0,
                attributes={"infra_kind": "terraform_resource", "resource_type": resource_type},
            ))

        for match in re.finditer(r'module\s+"(\w+)"', content):
            module_name = match.group(1)
            entities.append(DiscoveredEntity(
                entity_type="Infrastructure",
                entity_id=f"infra:module_{module_name}",
                name=f"module.{module_name}",
                source_document=path,
                provenance="OBSERVED",
                confidence=1.0,
                attributes={"infra_kind": "terraform_module"},
            ))

        return entities, relationships

    def _extract_python(self, path: str, content: str) -> tuple[list[DiscoveredEntity], list[dict]]:
        """Extract from Python pipeline files (Airflow DAGs, Spark jobs)."""
        import re

        name = Path(path).stem
        entities = []
        relationships = []

        # Airflow DAG
        dag_match = re.search(r'dag_id\s*=\s*["\']([^"\']+)["\']', content)
        if dag_match or "DAG(" in content:
            dag_name = dag_match.group(1) if dag_match else name
            entities.append(DiscoveredEntity(
                entity_type="Pipeline",
                entity_id=f"pipeline:{dag_name}",
                name=dag_name,
                source_document=path,
                provenance="OBSERVED",
                confidence=1.0,
                attributes={"pipeline_kind": "airflow_dag", "source_path": path},
            ))
        elif "SparkSession" in content or "spark" in content.lower():
            entities.append(DiscoveredEntity(
                entity_type="Pipeline",
                entity_id=f"pipeline:{name}",
                name=name,
                source_document=path,
                provenance="OBSERVED",
                confidence=0.9,
                attributes={"pipeline_kind": "spark_job", "source_path": path},
            ))

        return entities, relationships

    def _extract_infra(self, path: str, content: str, source_kind: str) -> list[DiscoveredEntity]:
        """Extract from Dockerfiles and compose files."""
        name = Path(path).stem if Path(path).stem != "Dockerfile" else Path(path).parent.name
        return [DiscoveredEntity(
            entity_type="Infrastructure",
            entity_id=f"infra:{name}",
            name=name,
            source_document=path,
            provenance="OBSERVED",
            confidence=1.0,
            attributes={"infra_kind": source_kind, "source_path": path},
        )]

    def _extract_ci(self, path: str, content: str) -> list[DiscoveredEntity]:
        """Extract from CI/CD workflow files."""
        name = Path(path).stem
        return [DiscoveredEntity(
            entity_type="Pipeline",
            entity_id=f"pipeline:ci_{name}",
            name=f"ci/{name}",
            source_document=path,
            provenance="OBSERVED",
            confidence=1.0,
            attributes={"pipeline_kind": "ci_workflow", "source_path": path},
        )]

    def _extract_yaml_config(self, path: str, content: str) -> list[DiscoveredEntity]:
        """Extract from YAML config files (dbt_project, quality checks)."""
        name = Path(path).stem
        return [DiscoveredEntity(
            entity_type="DataAsset",
            entity_id=f"dataasset:config_{name}",
            name=name,
            source_document=path,
            provenance="OBSERVED",
            confidence=0.8,
            attributes={"asset_kind": "configuration", "source_path": path},
        )]

    def _extract_json_config(self, path: str, content: str) -> list[DiscoveredEntity]:
        """Extract from JSON config files (governance, metadata)."""
        name = Path(path).stem
        return [DiscoveredEntity(
            entity_type="DataAsset",
            entity_id=f"dataasset:{name}",
            name=name,
            source_document=path,
            provenance="OBSERVED",
            confidence=0.8,
            attributes={"asset_kind": "metadata_config", "source_path": path},
        )]

    def _extract_delivery_structural(
        self, path: str, content: str, project_id: str
    ) -> tuple[list[DiscoveredEntity], list[dict]]:
        """Extract delivery entities from Markdown using heading structure."""
        import re

        name = Path(path).stem
        entities = [DiscoveredEntity(
            entity_type="DeliveryArtifact",
            entity_id=f"artifact:{name}",
            name=name,
            source_document=path,
            provenance="OBSERVED",
            confidence=0.9,
            attributes={"artifact_kind": "document", "source_path": path},
        )]

        # Look for checklist-like patterns
        checklist_items = re.findall(r"^[-*]\s+\[[ x]\]\s+(.+)$", content, re.MULTILINE)
        if checklist_items:
            entities.append(DiscoveredEntity(
                entity_type="Checklist",
                entity_id=f"checklist:{name}",
                name=f"{name} checklist",
                source_document=path,
                provenance="INFERRED",
                confidence=0.7,
                attributes={"items": checklist_items[:20], "item_count": len(checklist_items)},
            ))

        # Look for gate/approval patterns
        if any(kw in content.lower() for kw in ("gate", "approval", "sign-off", "exit criteria")):
            gate_name = f"gate_{name}"
            entities.append(DiscoveredEntity(
                entity_type="Gate",
                entity_id=f"gate:{gate_name}",
                name=gate_name,
                source_document=path,
                provenance="INFERRED",
                confidence=0.6,
                attributes={"source_path": path},
            ))

        return entities, []
