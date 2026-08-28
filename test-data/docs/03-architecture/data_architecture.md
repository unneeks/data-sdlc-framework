# Data Architecture

## Lakehouse Layer Design (Medallion Architecture)

### Bronze Layer (Raw/Landing)

- **Purpose**: Immutable record of source data exactly as received
- **Format**: Apache Iceberg tables (Parquet underlying)
- **Schema**: Mirrors source schema + metadata columns
- **Partitioning**: By ingestion_date (daily)
- **Retention**: Full history (no deletes except GDPR erasure)
- **Quality**: Schema validation only (no business rules)

Added metadata columns on all bronze tables:
```sql
_ingested_at       TIMESTAMP   -- UTC ingestion timestamp
_source_system     STRING      -- Source identifier (e.g., 'T24', 'SWIFT')
_batch_id          STRING      -- Unique batch/event identifier
_source_file       STRING      -- Source file path or Kafka topic:partition:offset
_cdc_operation     STRING      -- For CDC: INSERT, UPDATE, DELETE
```

### Silver Layer (Cleansed/Conformed)

- **Purpose**: Deduplicated, type-cast, validated, conformed data
- **Format**: Iceberg tables (Parquet, Zstd compression)
- **Schema**: Enterprise data model (standardised naming, types)
- **Partitioning**: Domain-specific (e.g., transactions by month)
- **Transformations**: Deduplication, type casting, null handling, conformity
- **Quality**: Full Great Expectations suite (schema + business rules)

### Gold Layer (Business/Consumption)

- **Purpose**: Business-ready aggregates, dimensions, and facts
- **Format**: Iceberg tables optimised for query patterns
- **Schema**: Star schema / data vault depending on domain
- **Partitioning**: Query-optimised (e.g., reporting_date, currency)
- **Transformations**: Business logic, aggregations, SCD Type 2, derived metrics
- **Quality**: Reconciliation against Oracle outputs during migration

### Iceberg Table Configuration

```yaml
# Standard Iceberg table properties
table_properties:
  format-version: 2
  write.format.default: parquet
  write.parquet.compression-codec: zstd
  write.metadata.delete-after-commit.enabled: true
  write.metadata.previous-versions-max: 100
  history.expire.max-snapshot-age-ms: 7776000000  # 90 days
  write.spark.fanout.enabled: true
```

### Schema Registry

All schemas registered in AWS Glue Schema Registry:
- Avro schemas for Kafka topics (streaming ingestion)
- Iceberg schemas for table definitions
- Schema evolution policy: backward-compatible only (additive columns)

### Data Modelling Approach

| Domain | Model Type | Rationale |
|--------|-----------|-----------|
| Customer | Data Vault 2.0 (Hub/Sat/Link) | Highly volatile, many source changes |
| Transactions | Fact table (immutable events) | Append-only, partitioned by date |
| Risk Scores | Snapshot fact (daily) | Point-in-time required for regulatory |
| Regulatory | Dimensional (star schema) | Optimised for report generation |
| FX Rates | Time-series fact | Tick data, partition by date |
| Counterparty | Data Vault 2.0 | Multi-source integration (KYC, LEI, sanctions) |

### Naming Conventions

```
Database:    atlas_{layer}_{domain}
             e.g., atlas_bronze_transactions, atlas_gold_risk

Table:       {entity}_{grain}
             e.g., customer_accounts, transaction_daily_summary

Column:      {entity}_{attribute} (snake_case)
             e.g., customer_id, transaction_amount_gbp

Partition:   {time_dimension}={value}
             e.g., transaction_date=2026-08-15
```

### Data Lifecycle Management

| Layer | Hot (S3 Standard) | Warm (S3 IA) | Cold (Glacier) |
|-------|-------------------|--------------|----------------|
| Bronze | 30 days | 90 days | After 90 days |
| Silver | 90 days | 1 year | After 1 year |
| Gold | 1 year | 3 years | After 3 years |
| Regulatory | 2 years | 5 years | After 5 years (retain 10 total) |
