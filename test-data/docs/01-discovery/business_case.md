# Business Case: Project ATLAS

## Executive Summary

Meridian Bank's Oracle Data Warehouse (commissioned 2012) has reached capacity and cost limits. Annual licensing exceeds GBP 4.2M, with growing technical debt in ETL pipelines (1,200+ Informatica mappings). The platform cannot support real-time analytics, ML workloads, or modern regulatory reporting timelines.

Project ATLAS proposes migration to an open-source lakehouse architecture on AWS, delivering 60% cost reduction, real-time capabilities, and regulatory agility.

## Current State Pain Points

| Issue | Impact | Severity |
|-------|--------|----------|
| Oracle licence renewal (2027) | GBP 4.2M/year + 8% annual escalation | HIGH |
| ETL batch window exceeded | SLA breaches 3x/quarter for regulatory reports | HIGH |
| No real-time capability | Cannot support PSD2 instant payment analytics | MEDIUM |
| Talent attrition | 4 of 6 Informatica developers resigned in 12 months | HIGH |
| Scalability ceiling | 95% storage utilisation, cannot onboard new domains | HIGH |
| Vendor lock-in | Single-vendor dependency for compute + storage + ETL | MEDIUM |

## Proposed Solution

### Target Architecture
- **Storage**: Apache Iceberg tables on Amazon S3 (open table format, no vendor lock-in)
- **Compute**: Apache Spark on EMR Serverless (elastic, pay-per-use)
- **Transformation**: dbt Core (SQL-first, version-controlled, testable)
- **Orchestration**: Apache Airflow on MWAA (managed, scalable)
- **Serving**: Trino (federated queries across lakehouse + operational systems)

### Strategic Benefits
1. **Cost**: 60% reduction in total platform cost (Year 1: GBP 1.7M vs GBP 4.2M)
2. **Agility**: New regulatory report delivery from 6 weeks to 5 days
3. **Real-time**: Stream processing for transaction monitoring (< 5 min latency)
4. **Talent**: Modern stack attracts and retains engineers
5. **Scalability**: Elastic compute, unlimited S3 storage
6. **Open standards**: No proprietary lock-in (Iceberg, Parquet, Avro)

## Financial Analysis

| Category | Year 1 | Year 2 | Year 3 | 5-Year Total |
|----------|--------|--------|--------|--------------|
| Migration Cost | GBP 3.8M | GBP 1.2M | - | GBP 5.0M |
| New Platform Run | GBP 1.7M | GBP 1.8M | GBP 1.9M | GBP 9.5M |
| Oracle Avoided | - | GBP 4.5M | GBP 4.9M | GBP 22.1M |
| **Net Benefit** | (GBP 3.8M) | GBP 2.7M | GBP 3.0M | **GBP 12.6M** |

**Payback period**: 18 months from go-live.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Data loss during migration | Low | Critical | Dual-run reconciliation for 3 months |
| Regulatory non-compliance | Medium | Critical | Engage compliance team from Phase 1 |
| Skills gap | Medium | High | Training programme + contractor augmentation |
| Business disruption | Low | High | Phased migration by domain, not big-bang |
| Timeline overrun | Medium | Medium | Agile delivery with 2-week sprints |

## Approval

| Approver | Role | Decision | Date |
|----------|------|----------|------|
| D. Morrison | CTO | APPROVED | 2026-01-15 |
| K. Sharma | CDO | APPROVED | 2026-01-18 |
| P. Hughes | CFO | APPROVED | 2026-01-22 |
| Board Investment Committee | - | APPROVED | 2026-02-01 |

## Success Criteria

1. All 6 data domains migrated and serving production queries
2. Oracle DWH decommissioned within 6 months of final domain go-live
3. All regulatory reports delivered from new platform with zero defects for 2 consecutive quarters
4. Platform total cost of ownership < GBP 2M/year
5. P95 query latency < 10 seconds for standard BI dashboards
6. Data freshness SLA: batch < 2 hours, streaming < 5 minutes
