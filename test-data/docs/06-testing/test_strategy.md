# Test Strategy — Project ATLAS

## Objectives

1. Validate data accuracy, completeness, and timeliness across all 6 domains post-migration
2. Ensure regulatory reports produce identical outputs to the legacy Oracle DWH during dual-run
3. Confirm platform meets non-functional requirements (latency, throughput, availability)
4. Provide confidence for Oracle decommissioning sign-off

## Testing Layers

| Layer | Scope | Tools | Frequency |
|-------|-------|-------|-----------|
| Unit | Individual Spark transforms, dbt model logic | pytest, dbt test | Every commit |
| Integration | Cross-service (ingestion → transformation → serving) | Great Expectations, custom harness | Per PR merge |
| Regression | Reconciliation vs Oracle DWH outputs | Recon framework (Spark-based) | Daily (dual-run) |
| Performance | Query latency, pipeline throughput, autoscaling | Locust, Spark History Server, CloudWatch | Weekly + pre-release |
| E2E | Full pipeline from source to BI dashboard | Airflow test DAGs, Selenium | Per release candidate |
| Security | AuthN/AuthZ, encryption, network isolation | Prowler, Checkov, pen-test (external) | Monthly + pre-release |

## Reconciliation (Dual-Run) Approach

During migration, every domain runs in parallel on both Oracle DWH and the new lakehouse. Reconciliation compares:

| Check | Tolerance | Action on Breach |
|-------|-----------|-----------------|
| Row counts (per table/model) | ±0.01% | Auto-alert, block promotion |
| Aggregate values (sums, averages) | ±0.001% | Auto-alert, manual triage |
| Regulatory report output (field-level) | Exact match | Block promotion, escalate to Compliance |
| Latency (batch pipeline end-to-end) | < 2 hours | Investigate, no auto-block |

Dual-run reconciliation must pass for **10 consecutive business days** before a domain is signed off for Oracle cutover.

## Data Quality Testing

Built into every pipeline run via:

- **dbt tests**: not_null, unique, accepted_values, relationships (400+ tests across all models)
- **Great Expectations**: statistical distribution checks, volume anomaly detection, schema validation
- **Soda**: row-level scans for PII leakage, format compliance (e.g., sort codes, IBANs)

## Performance Testing Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| P95 BI query latency (Trino) | < 10 seconds | Locust against Gold layer |
| Batch pipeline completion (daily) | < 2 hours end-to-end | Airflow SLA sensor |
| Streaming latency (CDC to Bronze) | < 5 minutes | Kafka consumer lag monitor |
| Spark job autoscale response | < 3 minutes to provision | EMR Serverless metrics |
| Concurrent users (Trino) | 50 analysts, no degradation | Load test simulation |

## Environment Strategy

| Stage | Data | Purpose |
|-------|------|---------|
| Unit/Local | Synthetic fixtures (100 rows) | Fast feedback on logic |
| Dev | Anonymised subset (10K rows) | Integration validation |
| Staging | Production-like volume (1M rows) | Performance + reconciliation |
| Prod (shadow) | Real data, read-only consumers | Final dual-run validation |

## Entry & Exit Criteria

### Entry (per domain)
- All ingestion pipelines deployed and producing data in staging
- dbt models compiled and passing seed tests
- Reconciliation framework configured for the domain

### Exit (per domain)
- 10-day reconciliation pass (zero breaches above tolerance)
- Performance targets met for 5 consecutive runs
- Security scan clear (no Critical/High findings)
- Sign-off from Data Owner, Compliance, and Platform Lead

## Defect Classification

| Severity | Definition | SLA |
|----------|-----------|-----|
| P1 — Critical | Data loss, regulatory report incorrect, platform down | Fix within 4 hours |
| P2 — High | SLA breach, data quality below threshold | Fix within 1 business day |
| P3 — Medium | Cosmetic data issues, performance degradation (within SLA) | Fix within 1 sprint |
| P4 — Low | Documentation gaps, minor UX issues in dashboards | Backlog |

## Tools & Reporting

- **Test orchestration**: Airflow (dedicated `test_*` DAGs)
- **Results storage**: Iceberg table `meta.test_results` (queryable history)
- **Dashboards**: Grafana board `project-atlas/testing` (live pass/fail rates)
- **Alerting**: Slack #atlas-testing, PagerDuty for P1
