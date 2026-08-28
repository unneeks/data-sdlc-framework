# Pipeline Design — Project ATLAS

## Pipeline Inventory

### Ingestion Pipelines

| Pipeline ID | Source | Target | Pattern | Frequency | Technology |
|-------------|--------|--------|---------|-----------|------------|
| ING-001 | Oracle DWH (CDC) | Raw Layer | CDC (Debezium) | Real-time | Kafka + Spark Streaming |
| ING-002 | Core Banking API | Raw Layer | API Pull | Every 15 min | Spark Batch |
| ING-003 | Market Data Feed | Raw Layer | Push/Stream | Real-time | Kafka Direct |
| ING-004 | Risk Engine Export | Raw Layer | File Drop (SFTP) | Daily 02:00 UTC | Spark Batch |
| ING-005 | Counterparty Registry | Raw Layer | API Pull (REST) | Daily 06:00 UTC | Spark Batch |

### Transformation Pipelines (dbt)

| Model Layer | Count | Materialisation | Description |
|-------------|-------|-----------------|-------------|
| Staging (`stg_`) | 12 | View / Incremental | 1:1 source cleansing, type casting, renaming |
| Intermediate (`int_`) | 8 | Incremental | Business logic joins, enrichment, deduplication |
| Marts (`mart_`) | 6 | Incremental (Z-ordered) | Consumption-ready aggregates and dimensions |

### Orchestration

All pipelines are orchestrated via Apache Airflow with the following DAG topology:

```
daily_ingestion_dag (02:00 UTC)
  ├── task: ingest_risk_scores
  ├── task: ingest_counterparty
  └── task: ingest_customer_snapshot
        │
        ▼
daily_dbt_dag (04:00 UTC, sensor waits for ingestion)
  ├── task: dbt_run_staging
  ├── task: dbt_run_intermediate
  ├── task: dbt_run_marts
  └── task: dbt_test
        │
        ▼
daily_quality_dag (06:00 UTC, sensor waits for dbt)
  ├── task: great_expectations_suite
  ├── task: soda_scan
  └── task: notify_data_stewards
        │
        ▼
streaming_monitor_dag (continuous)
  ├── sensor: kafka_lag_check (every 5 min)
  ├── task: alert_on_lag_breach
  └── task: checkpoint_health_metrics
```

## Error Handling & Retry Strategy

| Failure Type | Retry | Backoff | Alert | Escalation |
|-------------|-------|---------|-------|------------|
| Network timeout | 3x | Exponential (30s, 2min, 10min) | Slack #data-ops | PagerDuty after 3rd failure |
| Schema drift | 0 (fail fast) | N/A | Slack + Email | Immediate to Data Architect |
| Data quality | 0 (quarantine) | N/A | Slack #dq-alerts | Data Steward review |
| Resource limit | 2x | Linear (5min) | Slack #infra | SRE team |

## Data Quality Checkpoints

```
[Source] → VALIDATE_SCHEMA → [Raw] → VALIDATE_COMPLETENESS → [Staging] → VALIDATE_BUSINESS_RULES → [Curated]
```

Each transition includes:
1. Row count reconciliation (±0.01% tolerance)
2. Null check on NOT NULL columns
3. Referential integrity (foreign keys)
4. Business rule assertions (e.g., balance >= 0 for current accounts)
5. Statistical drift detection (column distributions)

## Idempotency

All pipelines are designed for safe re-execution:
- Iceberg's MERGE INTO with deduplication key
- dbt incremental models with `unique_key` and `on_schema_change='append_new_columns'`
- Airflow `max_active_runs=1` with `catchup=False` for streaming monitors
