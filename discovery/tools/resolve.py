"""Deterministic relationship resolution.

Takes relationship candidates (symbolic references like "depends on
stg_customers") and resolves them against the entity index (what
we've already discovered). No LLM — pure string matching and
heuristic resolution.
"""

from __future__ import annotations

from typing import Any

from discovery.result import DiscoveredEntity, DiscoveredRelationship, DiscoverySkip


def build_entity_index(entities: list[DiscoveredEntity]) -> dict[str, DiscoveredEntity]:
    """Build a lookup index from entity names/IDs for relationship resolution.

    Keys: lowercase name, entity_id, and type:name composite.
    """
    index: dict[str, DiscoveredEntity] = {}
    for entity in entities:
        index[entity.entity_id] = entity
        index[entity.name.lower()] = entity
        index[f"{entity.entity_type}:{entity.name}".lower()] = entity
        # Also index by filename stem (for dbt ref() style references)
        if "source_path" in entity.attributes:
            stem = entity.attributes["source_path"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
            index[stem.lower()] = entity
    return index


def _resolve_one(
    candidate: dict[str, Any],
    index: dict[str, DiscoveredEntity],
) -> DiscoveredRelationship | DiscoverySkip:
    """Resolve one relationship candidate against the index."""
    rel_type = candidate.get("relationship_type", "")
    source_name = candidate.get("source", "")
    target_name = candidate.get("target", "")
    confidence = candidate.get("confidence", 0.85)
    source_document = candidate.get("source_document", "")

    source_entity = (
        index.get(source_name)
        or index.get(source_name.lower())
        or index.get(f"Pipeline:{source_name}".lower())
        or index.get(f"DataAsset:{source_name}".lower())
    )
    target_entity = (
        index.get(target_name)
        or index.get(target_name.lower())
        or index.get(f"Pipeline:{target_name}".lower())
        or index.get(f"DataAsset:{target_name}".lower())
    )

    if source_entity is None:
        return DiscoverySkip(
            kind="unresolved_source",
            detail=f"relationship {rel_type}: source '{source_name}' not in entity index",
            source=source_document,
        )
    if target_entity is None:
        return DiscoverySkip(
            kind="unresolved_target",
            detail=f"relationship {rel_type}: target '{target_name}' not in entity index",
            source=source_document,
        )

    return DiscoveredRelationship(
        relationship_type=rel_type,
        source_ref=source_entity.entity_id,
        target_ref=target_entity.entity_id,
        confidence=confidence,
        source_document=source_document,
    )


def resolve_relationships(
    candidates: list[dict[str, Any]],
    entities: list[DiscoveredEntity],
) -> dict[str, Any]:
    """Resolve symbolic relationship candidates against discovered entities.

    Tool interface — returns a serializable dict.
    """
    index = build_entity_index(entities)
    resolved: list[DiscoveredRelationship] = []
    skipped: list[DiscoverySkip] = []

    for candidate in candidates:
        result = _resolve_one(candidate, index)
        if isinstance(result, DiscoveredRelationship):
            resolved.append(result)
        else:
            skipped.append(result)

    return {
        "total_candidates": len(candidates),
        "resolved": len(resolved),
        "skipped": len(skipped),
        "relationships": [
            {
                "relationship_type": r.relationship_type,
                "source_ref": r.source_ref,
                "target_ref": r.target_ref,
                "confidence": r.confidence,
            }
            for r in resolved
        ],
        "skipped_details": [
            {"kind": s.kind, "detail": s.detail, "source": s.source}
            for s in skipped
        ],
    }
