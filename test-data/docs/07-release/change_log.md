# Change Log — Project ATLAS

## Format

All notable changes to the ATLAS platform are documented here, following [Keep a Changelog](https://keepachangelog.com/) conventions.

---

## [0.4.0] — 2026-05-15 (Pre-release: Staging validation)

### Added
- Great Expectations integration for automated data quality gates
- Soda scans for PII detection in Bronze layer
- Grafana dashboards for pipeline health and data freshness

### Changed
- Upgraded EMR Serverless to 7.1 (Spark 3.5.1)
- Increased Kafka partition count for transactions topic (6 → 12)

### Fixed
- CDC connector missed DELETE events for soft-deleted accounts
- dbt incremental model `int_customer_enriched` duplicated rows on late-arriving data

---

## [0.3.0] — 2026-04-01 (Pre-release: Integration testing)

### Added
- Reconciliation framework (Spark job comparing Oracle vs Iceberg outputs)
- Alerting pipeline: Slack + PagerDuty integration
- Terraform module for Trino cluster (autoscaling 2–8 workers)

### Changed
- Switched dbt materialisation for mart models from table to incremental
- Reorganised DAG structure: split monolith into ingestion/transform/quality

### Fixed
- Airflow sensor timeout on large backfill runs (increased to 3600s)
- S3 lifecycle policy was archiving Bronze data too aggressively (30d → 365d)

---

## [0.2.0] — 2026-02-15 (Pre-release: Dev environment)

### Added
- Customer & Accounts domain: 5 ingestion pipelines, 12 staging models, 4 marts
- Apache Iceberg table format with Z-ordering on account_id
- dbt test suite (127 tests across staging and mart layers)
- Local Docker Compose for developer onboarding

### Changed
- Migrated from Glue Data Catalog to standalone Hive Metastore (Iceberg compatibility)

---

## [0.1.0] — 2026-01-20 (Pre-release: Infrastructure)

### Added
- Core AWS infrastructure via Terraform (VPC, S3 buckets, IAM roles, KMS keys)
- MWAA (Airflow) environment provisioned
- MSK (Kafka) cluster provisioned (3 brokers, multi-AZ)
- CI/CD pipeline (GitHub Actions → Terraform → AWS)
- Initial project documentation and ADRs
