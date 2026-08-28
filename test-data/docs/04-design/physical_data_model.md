# Physical Data Model — Project ATLAS

## Storage Architecture

### Lakehouse Layers (S3 + Apache Iceberg)

| Layer | S3 Path | Format | Retention |
|-------|---------|--------|-----------|
| Raw (Landing) | `s3://meridian-lake-raw/` | Avro/JSON (as-is) | 90 days |
| Staging (Cleansed) | `s3://meridian-lake-staging/` | Iceberg (Parquet) | 1 year |
| Curated (Modelled) | `s3://meridian-lake-curated/` | Iceberg (Parquet, Z-ordered) | 7 years |
| Archive | `s3://meridian-lake-archive/` | Iceberg (ORC, compressed) | 10+ years |

### Partitioning Strategy

| Table | Partition Spec | Sort Order | Rationale |
|-------|---------------|------------|-----------|
| transactions | `PARTITION BY days(txn_timestamp), bucket(16, account_id)` | `txn_timestamp DESC` | Query by date range + account |
| customer_accounts | `PARTITION BY bucket(32, customer_id)` | `customer_id` | Even distribution for joins |
| risk_scores | `PARTITION BY months(calc_date), model_version` | `calc_date DESC` | Version comparison queries |
| fx_rates | `PARTITION BY days(rate_timestamp)` | `base_ccy, quote_ccy` | Time-series + pair lookup |
| regulatory_reports | `PARTITION BY regime, years(reporting_period)` | `submission_date DESC` | Regime-specific queries |
| counterparty | `PARTITION BY bucket(8, counterparty_id)` | `counterparty_id` | Stable, moderate volume |

### Iceberg Table DDL Examples

```sql
-- Transactions (curated layer)
CREATE TABLE meridian_curated.transactions (
    txn_id              STRING      NOT NULL,
    account_id          STRING      NOT NULL,
    txn_type            STRING      NOT NULL,
    amount              DECIMAL(18,4) NOT NULL,
    currency            STRING      NOT NULL,
    txn_timestamp       TIMESTAMP   NOT NULL,
    counterparty_id     STRING,
    channel             STRING,
    status              STRING      NOT NULL,
    classification_code STRING,
    aml_flag            BOOLEAN     DEFAULT FALSE,
    _loaded_at          TIMESTAMP   NOT NULL,
    _source_system      STRING      NOT NULL,
    _batch_id           STRING      NOT NULL
)
USING iceberg
PARTITIONED BY (days(txn_timestamp), bucket(16, account_id))
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'zstd',
    'write.metadata.delete-after-commit.enabled' = 'true',
    'write.metadata.previous-versions-max' = '100',
    'read.split.target-size' = '134217728'
);

-- Customer Accounts (curated layer, SCD Type 2)
CREATE TABLE meridian_curated.customer_accounts (
    customer_id         STRING      NOT NULL,
    account_id          STRING      NOT NULL,
    account_type        STRING      NOT NULL,
    currency            STRING      NOT NULL,
    balance             DECIMAL(18,4),
    status              STRING      NOT NULL,
    opened_date         DATE        NOT NULL,
    closed_date         DATE,
    kyc_status          STRING,
    risk_tier           STRING,
    _valid_from         TIMESTAMP   NOT NULL,
    _valid_to           TIMESTAMP,
    _is_current         BOOLEAN     NOT NULL,
    _loaded_at          TIMESTAMP   NOT NULL
)
USING iceberg
PARTITIONED BY (bucket(32, customer_id));
```

### Metadata & Catalog

- **AWS Glue Data Catalog** as Iceberg metastore
- **Database naming**: `meridian_raw`, `meridian_staging`, `meridian_curated`
- **Table naming**: `{domain}_{entity}` (e.g., `txn_transactions`, `cust_accounts`)

### Compression & File Sizing

| Layer | Codec | Target File Size | Compaction |
|-------|-------|-----------------|------------|
| Raw | Snappy | 128MB | None |
| Staging | ZSTD (level 3) | 256MB | Daily |
| Curated | ZSTD (level 6) | 512MB | Daily + weekly optimize |

### Access Patterns

| Consumer | Access Method | SLA |
|----------|-------------|-----|
| dbt transformations | Spark/Iceberg direct | Batch (T+4h) |
| Regulatory reporting | Trino SQL | Interactive (<30s) |
| Risk dashboards | Trino + Superset | Interactive (<10s) |
| Data science notebooks | Spark direct read | Ad-hoc |
| Downstream APIs | Trino + caching | Sub-second (cached) |
