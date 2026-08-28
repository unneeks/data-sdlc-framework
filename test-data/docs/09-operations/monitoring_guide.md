# Monitoring Strategy — Project ATLAS

**Document ID:** ATLAS-OPS-MON-001  
**Version:** 2.0  
**Last Updated:** 2025-06-15  
**Owner:** Platform SRE Team  
**Classification:** Internal  

---

## 1. Overview

This document defines the monitoring strategy for the ATLAS data platform, covering observability across all layers: ingestion, transformation, serving, and governance. The strategy is designed to meet FCA operational resilience requirements (PS21/3) and PRA SS1/21 expectations for important business services.

### 1.1 Monitoring Principles

- **Defence in depth**: Monitor at infrastructure, application, data, and business layers
- **Alert on symptoms, not causes**: Alerts fire on user-facing impact first
- **Actionable alerts only**: Every alert must have a documented runbook response
- **Correlation over noise**: Aggregate related signals before alerting
- **Regulatory awareness**: Certain failures (data loss, PII exposure) have mandatory reporting timelines

---

## 2. Monitoring Architecture

### 2.1 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Metrics | Amazon CloudWatch + Prometheus | Infrastructure and application metrics |
| Logs | CloudWatch Logs + OpenSearch | Centralised log aggregation and search |
| Traces | AWS X-Ray + OpenTelemetry | Distributed tracing across pipeline stages |
| Dashboards | Apache Superset + CloudWatch Dashboards | Visualisation and operational awareness |
| Alerting | CloudWatch Alarms + PagerDuty | Alert routing and escalation |
| Synthetic Monitoring | CloudWatch Synthetics | End-to-end pipeline canaries |

### 2.2 Data Flow

```
[Pipeline Components] --> [CloudWatch Agent / OTel Collector] --> [CloudWatch Metrics/Logs]
                                                                         |
                                                                         v
                                                              [CloudWatch Alarms]
                                                                         |
                                                                         v
                                                              [PagerDuty / SNS]
                                                                         |
                                                                         v
                                                              [On-Call Engineer]
```

---

## 3. Dashboards

### 3.1 Executive Dashboard

**Audience:** CTO, Head of Data, Steering Committee  
**Refresh:** Every 15 minutes  
**Location:** Superset — `atlas-executive-health`

| Metric | Description | Target |
|--------|-------------|--------|
| Platform Availability | Percentage of time all critical pipelines are operational | >= 99.9% |
| Data Freshness SLA | Percentage of datasets meeting freshness targets | >= 99.5% |
| Regulatory Reporting Status | Status of all mandatory regulatory feeds | 100% on-time |
| Cost Efficiency | Monthly platform cost vs budget | Within 10% |

### 3.2 Pipeline Health Dashboard

**Audience:** Data Engineers, Platform SRE  
**Refresh:** Every 60 seconds  
**Location:** Superset — `atlas-pipeline-health`

| Metric | Description | Target |
|--------|-------------|--------|
| Pipeline Success Rate (24h) | Percentage of successful pipeline executions | >= 99.5% |
| Records Ingested | Total records processed across all pipelines | Baseline +/- 20% |
| Avg Ingestion Latency | Mean time from source change to lakehouse availability | < 30s (streaming), < 5min (batch) |
| CDC Lag | Maximum replication lag from Oracle/source systems | < 60s |
| Failed Pipelines | Count of pipeline failures requiring intervention | 0 |
| dbt Model Success Rate | Percentage of dbt models completing successfully | >= 99.8% |

### 3.3 Data Quality Dashboard

**Audience:** Data Stewards, Domain Owners  
**Refresh:** Every 5 minutes  
**Location:** Superset — `atlas-data-quality`

| Metric | Description | Target |
|--------|-------------|--------|
| Overall Quality Score | Composite score across all quality dimensions | >= 99.0% |
| Completeness | Percentage of non-null values in mandatory fields | >= 99.9% |
| Uniqueness | Duplicate record rate | < 0.01% |
| Freshness | Data staleness vs expected refresh cadence | Within 2x expected interval |
| Accuracy | Cross-validation against source system totals | Variance < 0.001% |

### 3.4 Infrastructure Dashboard

**Audience:** Platform SRE, Cloud Engineering  
**Refresh:** Every 30 seconds  
**Location:** CloudWatch Dashboard — `atlas-infrastructure`

| Metric | Description | Target |
|--------|-------------|--------|
| EKS Cluster Health | Node availability, pod scheduling success | 100% nodes healthy |
| MSK Cluster Health | Broker availability, under-replicated partitions | 0 under-replicated |
| Trino Query Performance | P50/P95/P99 query latency | P95 < 30s |
| S3 Request Rates | PUT/GET operations and error rates | Error rate < 0.1% |
| Glue Catalog Latency | Metastore API response times | P99 < 500ms |

---

## 4. Alerting Strategy

### 4.1 Severity Levels

| Severity | Definition | Response Time | Notification Channel | Example |
|----------|-----------|---------------|---------------------|---------|
| P1 — Critical | Complete service outage or data loss affecting regulatory reporting | 15 minutes | PagerDuty (phone call) + Slack #atlas-incidents | All pipelines halted, regulatory feed missed |
| P2 — High | Significant degradation affecting multiple consumers or SLA breach imminent | 30 minutes | PagerDuty (push) + Slack #atlas-alerts | Streaming latency > 5 min, dbt run failure on critical model |
| P3 — Medium | Single pipeline failure or quality issue not yet affecting consumers | 2 hours | Slack #atlas-alerts + Email | Non-critical batch job failure, quality score drop |
| P4 — Low | Informational, trend deviation, or cosmetic issue | Next business day | Slack #atlas-monitoring | Disk usage trending upward, minor latency increase |

### 4.2 Alert Definitions — Ingestion Layer

| Alert Name | Condition | Severity | Runbook |
|-----------|-----------|----------|---------|
| `ingestion.cdc.lag.critical` | CDC lag > 300s for > 5 minutes | P1 | RB-ING-001 |
| `ingestion.cdc.lag.warning` | CDC lag > 60s for > 10 minutes | P3 | RB-ING-001 |
| `ingestion.streaming.consumer.lag` | Kafka consumer lag > 100,000 messages | P2 | RB-ING-002 |
| `ingestion.streaming.throughput.drop` | Records/sec drops > 50% from baseline | P2 | RB-ING-003 |
| `ingestion.batch.failure` | Batch ingestion job fails | P3 | RB-ING-004 |
| `ingestion.batch.overdue` | Batch job not started within 30 min of schedule | P2 | RB-ING-005 |
| `ingestion.msk.under.replicated` | MSK under-replicated partitions > 0 | P2 | RB-ING-006 |
| `ingestion.msk.offline.partitions` | MSK offline partitions > 0 | P1 | RB-ING-007 |

### 4.3 Alert Definitions — Transformation Layer

| Alert Name | Condition | Severity | Runbook |
|-----------|-----------|----------|---------|
| `transform.dbt.run.failure` | dbt run fails on Tier 1 model | P2 | RB-TRF-001 |
| `transform.dbt.run.failure.noncritical` | dbt run fails on Tier 2/3 model | P3 | RB-TRF-001 |
| `transform.dbt.duration.exceeded` | Model execution > 3x historical average | P3 | RB-TRF-002 |
| `transform.dbt.freshness.stale` | Source freshness check fails | P2 | RB-TRF-003 |
| `transform.spark.job.failure` | Spark transformation job fails | P2 | RB-TRF-004 |
| `transform.spark.oom` | Spark executor OOM kills | P3 | RB-TRF-005 |

### 4.4 Alert Definitions — Serving Layer

| Alert Name | Condition | Severity | Runbook |
|-----------|-----------|----------|---------|
| `serving.trino.query.timeout` | Query timeout rate > 5% over 5 minutes | P2 | RB-SRV-001 |
| `serving.trino.query.failure` | Query failure rate > 10% over 5 minutes | P1 | RB-SRV-002 |
| `serving.trino.memory.exhausted` | Cluster memory > 90% for > 10 minutes | P2 | RB-SRV-003 |
| `serving.trino.worker.down` | Worker node count < minimum threshold | P2 | RB-SRV-004 |
| `serving.superset.unavailable` | Superset health check fails for > 2 minutes | P3 | RB-SRV-005 |

### 4.5 Alert Definitions — Data Quality

| Alert Name | Condition | Severity | Runbook |
|-----------|-----------|----------|---------|
| `quality.score.critical` | Quality score < 95% on Tier 1 table | P1 | RB-DQ-001 |
| `quality.score.warning` | Quality score < 99% on Tier 1 table | P3 | RB-DQ-001 |
| `quality.reconciliation.mismatch` | Source-target record count variance > 0.01% | P2 | RB-DQ-002 |
| `quality.schema.drift` | Unexpected schema change detected | P2 | RB-DQ-003 |
| `quality.null.spike` | NULL rate increase > 5x baseline | P2 | RB-DQ-004 |
| `quality.duplicate.detected` | Duplicate records found in Tier 1 table | P2 | RB-DQ-005 |

### 4.6 Alert Definitions — Security & Compliance

| Alert Name | Condition | Severity | Runbook |
|-----------|-----------|----------|---------|
| `security.pii.unauthorized.access` | Access to PII data by non-authorised role | P1 | RB-SEC-001 |
| `security.bulk.export` | Bulk data export > 1M records without approval | P1 | RB-SEC-002 |
| `security.kms.key.rotation.overdue` | KMS key rotation > policy threshold | P2 | RB-SEC-003 |
| `compliance.retention.violation` | Data retained beyond retention policy period | P2 | RB-SEC-004 |

---

## 5. Thresholds and Baselines

### 5.1 Baseline Establishment

Baselines are computed using a 4-week rolling window with weekday/weekend segmentation:

- **Throughput baseline**: Mean records/minute per pipeline, segmented by hour-of-day
- **Latency baseline**: P50 and P95 latency per pipeline over 4-week window
- **Quality baseline**: Moving average quality score with 1% tolerance band
- **Cost baseline**: Daily cost per pipeline normalised by record volume

### 5.2 Dynamic Thresholds

Alerts use dynamic thresholds where appropriate:

- Standard deviation-based: Alert fires at mean + 3 sigma
- Percentage deviation: Alert fires at > 50% deviation from baseline
- Rate of change: Alert fires on sustained gradient exceeding historical pattern

---

## 6. Escalation Paths

### 6.1 Standard Escalation Matrix

| Time Since Alert | Action | Responsible |
|-----------------|--------|-------------|
| 0 min | Alert fires, PagerDuty notifies on-call | Automated |
| 15 min (P1) / 30 min (P2) | On-call acknowledges and begins investigation | On-Call Engineer |
| 30 min (P1) / 1 hour (P2) | If unresolved, escalate to secondary on-call | On-Call Engineer |
| 1 hour (P1) / 2 hours (P2) | Escalate to Engineering Manager | Secondary On-Call |
| 2 hours (P1) | Incident Commander engaged, stakeholder comms begin | Engineering Manager |
| 4 hours (P1) | Executive escalation (Head of Data, CTO) | Incident Commander |

### 6.2 Regulatory Escalation

For incidents affecting regulatory reporting:

| Timeframe | Action |
|-----------|--------|
| Immediately | Assess impact on regulatory feeds (FCA, PRA, BOE Statistical) |
| Within 1 hour | Notify Compliance team of potential regulatory impact |
| Within 4 hours | Formal assessment: can regulatory deadline still be met? |
| T-2 hours before deadline | If at risk: notify Head of Regulatory Reporting for manual contingency |
| Post-deadline (if missed) | FCA/PRA notification process per Incident Response Plan IRP-2024-001 |

---

## 7. On-Call Rotation

### 7.1 Structure

- **Primary on-call**: Rotates weekly among Data Engineering team (6 engineers)
- **Secondary on-call**: Rotates weekly among Platform SRE team (4 engineers)
- **Management escalation**: Engineering Manager (always reachable for P1)

### 7.2 Handover Process

- Handover occurs every Monday at 09:00 UTC
- Outgoing on-call provides written handover in Slack #atlas-oncall
- Handover includes: open incidents, known issues, upcoming maintenance windows
- Incoming on-call confirms receipt and reviews dashboard state

### 7.3 Out-of-Hours Coverage

- P1 alerts: 24/7/365 — PagerDuty phone call escalation
- P2 alerts: 24/7/365 — PagerDuty push notification
- P3 alerts: Business hours only (08:00-18:00 UTC, Mon-Fri)
- P4 alerts: Next business day

---

## 8. Synthetic Monitoring

### 8.1 Pipeline Canaries

Synthetic canary pipelines run every 5 minutes to validate end-to-end path:

| Canary | Description | Expected Latency |
|--------|-------------|-----------------|
| `canary-cdc-roundtrip` | Insert test record in source, verify arrival in lakehouse | < 60s |
| `canary-streaming-e2e` | Publish to Kafka, verify in Iceberg table | < 30s |
| `canary-dbt-model` | Trigger dbt model on test schema, verify output | < 120s |
| `canary-trino-query` | Execute standard query set against Trino | < 10s |
| `canary-superset-render` | Load critical dashboard, verify render | < 15s |

### 8.2 Data Reconciliation Checks

Daily automated reconciliation between:

- Oracle source system record counts vs lakehouse raw layer
- Raw layer record counts vs curated layer
- Curated layer financial totals vs General Ledger control totals
- Regulatory report outputs vs independent calculation

---

## 9. Operational Metrics and SLIs/SLOs

### 9.1 Service Level Indicators (SLIs)

| SLI | Measurement | Good Event |
|-----|-------------|------------|
| Ingestion Availability | Pipeline execution status | Execution completes without error |
| Ingestion Latency | Time from source to lakehouse | < 30s for streaming, < 5 min for batch |
| Query Availability | Trino query success rate | Query returns without error |
| Query Latency | Trino query response time | P95 < 30 seconds |
| Data Freshness | Age of most recent record | Within 2x expected refresh interval |
| Data Quality | Quality check pass rate | All checks pass |

### 9.2 Service Level Objectives (SLOs)

| SLO | Target | Error Budget (monthly) | Measurement Window |
|-----|--------|----------------------|-------------------|
| Pipeline Availability | 99.9% | 43.2 minutes | 30-day rolling |
| Streaming Latency | 99.5% within 30s | 0.5% over threshold | 30-day rolling |
| Query Availability | 99.95% | 21.6 minutes | 30-day rolling |
| Data Freshness | 99.5% within SLA | 3.6 hours stale | 30-day rolling |
| Data Quality (Tier 1) | 99.9% checks passing | 43.2 minutes failing | 30-day rolling |

---

## 10. Review and Continuous Improvement

### 10.1 Review Cadence

| Activity | Frequency | Participants |
|----------|-----------|-------------|
| Alert noise review | Weekly | On-call engineers |
| SLO burn rate review | Weekly | Engineering Manager + SRE |
| Dashboard effectiveness review | Monthly | All consumers |
| Threshold tuning | Monthly | Data Engineering + SRE |
| Monitoring strategy review | Quarterly | Head of Data + CTO |
| Incident post-mortem | Per P1/P2 incident | All involved + management |

### 10.2 Alert Hygiene

- Alerts not actioned for 30 days are reviewed for removal
- False positive rate target: < 5% per alert definition
- Every alert must link to a runbook within 7 days of creation or be deleted
- On-call engineers log alert quality feedback in PagerDuty
