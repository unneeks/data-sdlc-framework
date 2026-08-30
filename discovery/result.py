"""Discovery result types — shared across all strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoverySkip:
    """A file or entity that was intentionally skipped."""
    kind: str
    detail: str
    source: str


@dataclass
class DiscoveryFailure:
    """A file or entity that failed extraction or ingestion."""
    kind: str
    detail: str
    source: str


@dataclass
class DiscoveredEntity:
    """One entity extracted from a source file."""
    entity_type: str
    entity_id: str
    name: str
    source_document: str
    provenance: str = "INFERRED"
    confidence: float = 0.85
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredRelationship:
    """One relationship between two discovered entities."""
    relationship_type: str
    source_ref: str
    target_ref: str
    confidence: float = 0.85
    source_document: str = ""


@dataclass
class DiscoveryReport:
    """The complete output of one discovery run."""
    project_id: str
    strategy: str
    skill: str
    entities_discovered: int = 0
    relationships_discovered: int = 0
    entities_by_type: dict[str, int] = field(default_factory=dict)
    entities: list[DiscoveredEntity] = field(default_factory=list)
    relationships: list[DiscoveredRelationship] = field(default_factory=list)
    skipped: list[DiscoverySkip] = field(default_factory=list)
    failed: list[DiscoveryFailure] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Discovery Report [{self.strategy}] skill={self.skill}",
            f"  Project: {self.project_id}",
            f"  Entities: {self.entities_discovered}",
            f"  Relationships: {self.relationships_discovered}",
            f"  By type: {self.entities_by_type}",
            f"  Skipped: {len(self.skipped)}",
            f"  Failed: {len(self.failed)}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "strategy": self.strategy,
            "skill": self.skill,
            "entities_discovered": self.entities_discovered,
            "relationships_discovered": self.relationships_discovered,
            "entities_by_type": self.entities_by_type,
            "skipped": [{"kind": s.kind, "detail": s.detail, "source": s.source} for s in self.skipped],
            "failed": [{"kind": f.kind, "detail": f.detail, "source": f.source} for f in self.failed],
        }
