"""Deterministic discovery tools — shared across all strategies.

These are the constant layer: every strategy calls the same tools,
just orchestrated differently. Each tool is a pure function with no
LLM dependency. They can be exposed as MCP tools, Lambda functions,
or called directly in-process.
"""

from discovery.tools.walk import walk_repository, classify_file
from discovery.tools.read import read_file, read_files_batch
from discovery.tools.resolve import resolve_relationships, build_entity_index
from discovery.tools.ingest import ingest_entities, ingest_relationships
from discovery.tools.deep_walk import deep_walk_repository

__all__ = [
    "build_entity_index",
    "classify_file",
    "deep_walk_repository",
    "ingest_entities",
    "ingest_relationships",
    "read_file",
    "read_files_batch",
    "resolve_relationships",
    "walk_repository",
]
