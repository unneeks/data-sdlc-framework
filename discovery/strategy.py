"""The DiscoveryStrategy protocol — one interface, four implementations.

Tools are constant. Strategies are swappable. Skills are the strategy's
sub-variable. Each strategy orchestrates the same deterministic tools
in a different execution context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from discovery.result import DiscoveryReport


@dataclass(frozen=True)
class DiscoveryConfig:
    """Everything a strategy needs to run discovery against one repository."""

    project_id: str
    repository_root: Path
    repository_id: str | None = None
    skill: str = "repository-discovery"
    on_error: Literal["fail_fast", "collect"] = "collect"
    extra_exclude_dirs: frozenset[str] = field(default_factory=frozenset)


class DiscoveryStrategy(Protocol):
    """How discovery is orchestrated — swappable without touching tools."""

    @property
    def name(self) -> str:
        """Strategy identifier (local, harness, runtime, claude-code)."""
        ...

    def discover(self, config: DiscoveryConfig) -> DiscoveryReport:
        """Walk the repository and populate the knowledge graph.

        Returns a report of what was discovered, skipped, and failed.
        """
        ...
