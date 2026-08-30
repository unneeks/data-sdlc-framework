"""Local strategy — Python orchestration loop with ExtractionClient for LLM.

The original discover_project() logic: walk files, send each to an LLM
extraction client, parse responses, resolve relationships, ingest.
No external service dependency beyond the LLM API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from discovery.result import (
    DiscoveredEntity,
    DiscoveredRelationship,
    DiscoveryFailure,
    DiscoveryReport,
    DiscoverySkip,
)
from discovery.strategy import DiscoveryConfig
from discovery.tools.walk import walk_repository, SOURCE_KIND_ENTITY_TYPES
from discovery.tools.read import read_file
from discovery.tools.resolve import resolve_relationships, build_entity_index
from discovery.tools.ingest import ingest_entities, ingest_relationships


class ExtractionClient(Protocol):
    """One prompt + schema → one structured response."""
    def extract(self, *, prompt: str, response_schema: dict[str, Any]) -> dict[str, Any]: ...


class LocalStrategy:
    """Pure Python orchestration. Uses ExtractionClient for LLM calls.

    Four passes:
      1. Walk and classify (deterministic)
      2. Technical extraction (LLM per file)
      3. Delivery extraction (LLM per file, given technical index)
      4. Resolve relationships + ingest (deterministic)
    """

    name = "local"

    def __init__(self, client: ExtractionClient):
        self._client = client

    def discover(self, config: DiscoveryConfig) -> DiscoveryReport:
        walk_result = walk_repository(
            str(config.repository_root),
            extra_exclude_dirs=list(config.extra_exclude_dirs),
        )

        all_entities: list[DiscoveredEntity] = []
        all_rel_candidates: list[dict[str, Any]] = []
        skipped: list[DiscoverySkip] = []
        failed: list[DiscoveryFailure] = []

        # Pass 2: Technical extraction
        for candidate in walk_result["technical"]:
            file_result = read_file(str(config.repository_root), candidate["path"])
            if "error" in file_result:
                skipped.append(DiscoverySkip(
                    kind=file_result["error"],
                    detail=file_result.get("detail", file_result["error"]),
                    source=candidate["path"],
                ))
                continue

            prompt = self._build_technical_prompt(
                candidate["path"], file_result["content"], candidate["source_kind"]
            )
            schema = self._technical_response_schema(candidate["entity_types"])

            try:
                raw = self._client.extract(prompt=prompt, response_schema=schema)
                entities, rels = self._parse_technical_response(
                    raw, candidate["path"], config.project_id
                )
                all_entities.extend(entities)
                all_rel_candidates.extend(rels)
            except Exception as e:
                if config.on_error == "fail_fast":
                    raise
                failed.append(DiscoveryFailure(
                    kind="extraction_failed",
                    detail=str(e),
                    source=candidate["path"],
                ))

        # Pass 3: Delivery extraction (with knowledge of technical entities)
        known_entity_names = [e.name for e in all_entities]
        for candidate in walk_result["delivery"]:
            file_result = read_file(str(config.repository_root), candidate["path"])
            if "error" in file_result:
                skipped.append(DiscoverySkip(
                    kind=file_result["error"],
                    detail=file_result.get("detail", file_result["error"]),
                    source=candidate["path"],
                ))
                continue

            prompt = self._build_delivery_prompt(
                candidate["path"], file_result["content"], known_entity_names
            )
            schema = self._delivery_response_schema()

            try:
                raw = self._client.extract(prompt=prompt, response_schema=schema)
                entities, rels = self._parse_delivery_response(
                    raw, candidate["path"], config.project_id
                )
                all_entities.extend(entities)
                all_rel_candidates.extend(rels)
            except Exception as e:
                if config.on_error == "fail_fast":
                    raise
                failed.append(DiscoveryFailure(
                    kind="extraction_failed",
                    detail=str(e),
                    source=candidate["path"],
                ))

        # Pass 4: Resolve + Ingest
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
            strategy=self.name,
            skill=config.skill,
            entities_discovered=ingest_result["ingested"],
            relationships_discovered=rel_ingest["ingested"],
            entities_by_type=by_type,
            entities=all_entities,
            relationships=[
                DiscoveredRelationship(**r) for r in resolution["relationships"]
            ],
            skipped=skipped,
            failed=failed,
        )

    def _build_technical_prompt(self, path: str, content: str, source_kind: str) -> str:
        entity_types = SOURCE_KIND_ENTITY_TYPES.get(source_kind, ())
        return (
            f"Extract entities from this {source_kind} file.\n"
            f"File: {path}\n"
            f"Legal entity types: {', '.join(entity_types)}\n\n"
            f"For each entity, provide: name, entity_type, description, dependencies.\n"
            f"For relationships, provide: source (entity name), target (entity name), "
            f"relationship_type (DEPENDS_ON, PRODUCES, HAS_SCHEMA, CONTAINS).\n\n"
            f"```\n{content}\n```"
        )

    def _build_delivery_prompt(self, path: str, content: str, known_entities: list[str]) -> str:
        entity_list = "\n".join(f"  - {name}" for name in known_entities[:50])
        return (
            f"Extract delivery entities from this document.\n"
            f"File: {path}\n"
            f"Legal entity types: Task, Checklist, Gate, DeliveryArtifact, EvidenceRequirement\n\n"
            f"Known technical entities (link to these with DESCRIBES/GOVERNS):\n{entity_list}\n\n"
            f"```\n{content}\n```"
        )

    def _technical_response_schema(self, entity_types: list[str]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "entity_type": {"type": "string", "enum": list(entity_types)},
                            "description": {"type": "string"},
                            "dependencies": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "entity_type"],
                    },
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "relationship_type": {"type": "string"},
                        },
                        "required": ["source", "target", "relationship_type"],
                    },
                },
            },
        }

    def _delivery_response_schema(self) -> dict[str, Any]:
        return self._technical_response_schema(
            ["Task", "Checklist", "Gate", "DeliveryArtifact", "EvidenceRequirement"]
        )

    def _parse_technical_response(
        self, raw: dict[str, Any], source_document: str, project_id: str
    ) -> tuple[list[DiscoveredEntity], list[dict[str, Any]]]:
        entities = []
        for item in raw.get("entities", []):
            entities.append(DiscoveredEntity(
                entity_type=item["entity_type"],
                entity_id=f"{item['entity_type'].lower()}:{item['name'].lower().replace(' ', '_')}",
                name=item["name"],
                source_document=source_document,
                attributes={"description": item.get("description", ""), "dependencies": item.get("dependencies", [])},
            ))
        rels = [
            {**r, "source_document": source_document}
            for r in raw.get("relationships", [])
        ]
        return entities, rels

    def _parse_delivery_response(
        self, raw: dict[str, Any], source_document: str, project_id: str
    ) -> tuple[list[DiscoveredEntity], list[dict[str, Any]]]:
        return self._parse_technical_response(raw, source_document, project_id)
