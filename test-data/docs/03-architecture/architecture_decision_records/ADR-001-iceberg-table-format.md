# ADR-001: Apache Iceberg as Table Format

## Status
ACCEPTED (2026-02-15)

## Context
We need an open table format for the lakehouse that supports ACID transactions, schema evolution, time travel, and partition evolution without vendor lock-in.

## Options Considered
1. **Apache Iceberg** - Open format, strong community, excellent Spark/Trino support
2. **Delta Lake** - Databricks-originated, good but tighter coupling to Spark/Databricks
3. **Apache Hudi** - Strong CDC support but more complex operational model

## Decision
Adopt Apache Iceberg v2 format for all lakehouse tables.

## Rationale
- Iceberg is engine-agnostic: works with Spark, Trino, Flink, Dremio without modification
- Format v2 supports row-level deletes (required for GDPR erasure)
- Schema evolution is first-class (add/rename/reorder columns without rewrite)
- Partition evolution allows changing partition strategy without data migration
- AWS Glue Data Catalog natively supports Iceberg (no separate metastore needed)
- Strongest community momentum in 2025-2026 (adopted by Apple, Netflix, LinkedIn, AWS)

## Consequences
- Team must learn Iceberg-specific maintenance (compaction, snapshot expiry, orphan file cleanup)
- Must use Iceberg-aware engines only (no raw Parquet readers bypassing metadata)
- Catalog choice is coupled to Iceberg (AWS Glue Catalog selected as complement)
