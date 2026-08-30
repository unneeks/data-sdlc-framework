"""Knowledge graph ingestion tools.

Writes discovered entities and relationships to the graph store.
Deterministic — validates structure, assigns provenance metadata,
and writes. No LLM dependency.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from discovery.result import DiscoveredEntity, DiscoveredRelationship, DiscoveryFailure


# In-memory graph store (replaced by real persistence in production)
_graph_store: dict[str, Any] = {
    "entities": {},
    "relationships": [],
    "projects": {},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_id(entity_type: str, name: str) -> str:
    """Deterministic ID from type + name."""
    slug = name.lower().replace(" ", "_").replace("/", "_").replace(".", "_")
    return f"{entity_type.lower()}:{slug}"


def ingest_entities(
    project_id: str,
    entities: list[dict[str, Any]],
    *,
    discovered_by: str = "discovery@0.1.0",
) -> dict[str, Any]:
    """Validate and ingest entities into the knowledge graph.

    Tool interface — takes raw extraction output, assigns identity
    and provenance, writes to store. Returns ingestion report.
    """
    if project_id not in _graph_store["projects"]:
        _graph_store["projects"][project_id] = {
            "id": project_id,
            "created_at": _utc_now(),
            "entity_count": 0,
            "relationship_count": 0,
        }

    ingested: list[DiscoveredEntity] = []
    failed: list[DiscoveryFailure] = []

    for raw in entities:
        entity_type = raw.get("entity_type")
        name = raw.get("name")

        if not entity_type or not name:
            failed.append(DiscoveryFailure(
                kind="missing_required_field",
                detail=f"entity_type={entity_type}, name={name}",
                source=raw.get("source_document", "unknown"),
            ))
            continue

        entity_id = raw.get("entity_id") or _generate_id(entity_type, name)
        entity = DiscoveredEntity(
            entity_type=entity_type,
            entity_id=entity_id,
            name=name,
            source_document=raw.get("source_document", ""),
            provenance=raw.get("provenance", "INFERRED"),
            confidence=raw.get("confidence", 0.85),
            attributes=raw.get("attributes", {}),
        )

        _graph_store["entities"][entity_id] = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "name": name,
            "project_id": project_id,
            "provenance": entity.provenance,
            "confidence": entity.confidence,
            "discovered_by": discovered_by,
            "discovered_at": _utc_now(),
            "source_document": entity.source_document,
            "attributes": entity.attributes,
        }
        ingested.append(entity)

    _graph_store["projects"][project_id]["entity_count"] = sum(
        1 for e in _graph_store["entities"].values() if e["project_id"] == project_id
    )

    by_type: dict[str, int] = {}
    for e in ingested:
        by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1

    return {
        "project_id": project_id,
        "ingested": len(ingested),
        "failed": len(failed),
        "by_type": by_type,
        "failures": [{"kind": f.kind, "detail": f.detail, "source": f.source} for f in failed],
    }


def _resolve_ref(ref: str) -> str | None:
    """Resolve a reference to an entity_id. Tries exact match, then name lookup."""
    if ref in _graph_store["entities"]:
        return ref
    # Try lowercase name match
    ref_lower = ref.lower().replace(" ", "_").replace("/", "_").replace(".", "_")
    for entity_id, entity in _graph_store["entities"].items():
        if entity["name"].lower() == ref.lower():
            return entity_id
        if entity_id == ref_lower:
            return entity_id
        # Try type:name pattern
        slug = entity["name"].lower().replace(" ", "_").replace("/", "_").replace(".", "_")
        if slug == ref_lower:
            return entity_id
    return None


def ingest_relationships(
    project_id: str,
    relationships: list[dict[str, Any]],
    *,
    discovered_by: str = "discovery@0.1.0",
) -> dict[str, Any]:
    """Validate and ingest relationships into the knowledge graph.

    Both source and target must exist in the entity store.
    Resolves references by entity_id or name.
    """
    ingested = 0
    failed: list[DiscoveryFailure] = []

    for raw in relationships:
        rel_type = raw.get("relationship_type")
        source_ref = raw.get("source_ref")
        target_ref = raw.get("target_ref")

        if not rel_type or not source_ref or not target_ref:
            failed.append(DiscoveryFailure(
                kind="missing_required_field",
                detail=f"type={rel_type}, source={source_ref}, target={target_ref}",
                source=raw.get("source_document", "unknown"),
            ))
            continue

        resolved_source = _resolve_ref(source_ref)
        if resolved_source is None:
            failed.append(DiscoveryFailure(
                kind="dangling_source",
                detail=f"{rel_type}: source '{source_ref}' not in graph",
                source=raw.get("source_document", "unknown"),
            ))
            continue

        resolved_target = _resolve_ref(target_ref)
        if resolved_target is None:
            failed.append(DiscoveryFailure(
                kind="dangling_target",
                detail=f"{rel_type}: target '{target_ref}' not in graph",
                source=raw.get("source_document", "unknown"),
            ))
            continue

        source_ref = resolved_source
        target_ref = resolved_target

        _graph_store["relationships"].append({
            "id": str(uuid.uuid4()),
            "relationship_type": rel_type,
            "source_ref": source_ref,
            "target_ref": target_ref,
            "project_id": project_id,
            "confidence": raw.get("confidence", 0.85),
            "discovered_by": discovered_by,
            "discovered_at": _utc_now(),
        })
        ingested += 1

    _graph_store["projects"][project_id]["relationship_count"] = sum(
        1 for r in _graph_store["relationships"] if r["project_id"] == project_id
    )

    return {
        "project_id": project_id,
        "ingested": ingested,
        "failed": len(failed),
        "failures": [{"kind": f.kind, "detail": f.detail, "source": f.source} for f in failed],
    }


def get_graph_state(project_id: str | None = None) -> dict[str, Any]:
    """Query current graph state. Useful for debugging and the API."""
    if project_id:
        entities = {k: v for k, v in _graph_store["entities"].items() if v["project_id"] == project_id}
        relationships = [r for r in _graph_store["relationships"] if r["project_id"] == project_id]
    else:
        entities = _graph_store["entities"]
        relationships = _graph_store["relationships"]

    return {
        "projects": list(_graph_store["projects"].values()),
        "entity_count": len(entities),
        "relationship_count": len(relationships),
        "entities": list(entities.values()),
        "relationships": relationships,
    }


def reset_graph() -> None:
    """Reset the in-memory graph store. For testing."""
    _graph_store["entities"].clear()
    _graph_store["relationships"].clear()
    _graph_store["projects"].clear()
