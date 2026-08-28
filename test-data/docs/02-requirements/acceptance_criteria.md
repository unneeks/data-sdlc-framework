# Acceptance Criteria

## Project ATLAS — Migration Acceptance Gates

### AC-001: Data Completeness

- [ ] All 3,847 source tables have been assessed (migrate, archive, or decommission)
- [ ] All 1,204 actively-queried tables are migrated to Iceberg format
- [ ] Row counts reconcile between Oracle and lakehouse (tolerance: 0 for dimensions, < 0.01% for facts)
- [ ] All 47 regulatory report datasets produce identical output from new platform
- [ ] Historical data loaded: 7 years transactions, 5 years risk, 10 years regulatory

### AC-002: Data Quality

- [ ] Data quality score > 95% across all domains (measured by Great Expectations)
- [ ] Zero critical data quality failures in production for 14 consecutive days
- [ ] All PII fields identified, classified, and masked in non-production environments
- [ ] Referential integrity maintained: zero orphan records in customer-transaction join
- [ ] Schema validation passes on 100% of ingestion batches

### AC-003: Performance

- [ ] Batch ingestion completes within 2-hour SLA (measured over 30 days)
- [ ] Streaming latency < 5 minutes P99 (measured over 30 days)
- [ ] Full dbt daily run completes in < 90 minutes
- [ ] P95 analytical query response < 10 seconds (top 50 queries by frequency)
- [ ] Regulatory report generation < 30 minutes per report
- [ ] 200 concurrent users supported without degradation (load test evidence)

### AC-004: Security & Compliance

- [ ] All data encrypted at rest (AES-256) and in transit (TLS 1.3)
- [ ] Column-level access controls enforce PII masking for non-authorised roles
- [ ] SOX ITGC controls documented and evidenced (segregation of duties, change management)
- [ ] Penetration test completed with zero critical/high findings
- [ ] DPIA (Data Protection Impact Assessment) approved by DPO
- [ ] All data resides in eu-west-2 (London region) — no cross-region replication

### AC-005: Operational Readiness

- [ ] Operational runbook created and tested (DR drill successful)
- [ ] Monitoring dashboards operational (Grafana: ingestion, quality, SLA, cost)
- [ ] Alerting configured: P1 alerts reach on-call within 5 minutes
- [ ] On-call rota established with minimum 2 trained engineers per shift
- [ ] Rollback procedure tested: can revert to Oracle within 4 hours
- [ ] BAU support model agreed with 24/7 coverage for P1

### AC-006: Business Validation

- [ ] All downstream systems (Risk Engine, AxiomSL, SAP, Tableau) migrated to new endpoints
- [ ] Business UAT signed off by domain owners (Risk, Regulatory, Finance)
- [ ] 90-day parallel run completed with zero discrepancies in regulatory outputs
- [ ] End-user training delivered to 200+ analysts
- [ ] Business glossary published with > 90% coverage of gold-layer tables

### AC-007: Decommissioning Readiness

- [ ] Oracle read traffic reduced to zero for 30 consecutive days
- [ ] All Informatica workflows disabled with no downstream impact
- [ ] Oracle backup archived to cold storage (S3 Glacier Deep Archive)
- [ ] Licence termination notice submitted to Oracle (90-day notice period)
- [ ] Decommissioning plan approved by Change Advisory Board

### Sign-off Matrix

| Criterion Group | Approver | Sign-off Required By |
|----------------|----------|---------------------|
| AC-001 (Completeness) | Data Architect | Go-Live - 2 weeks |
| AC-002 (Quality) | QA Lead | Go-Live - 1 week |
| AC-003 (Performance) | Solution Architect | Go-Live - 1 week |
| AC-004 (Security) | CISO | Go-Live - 2 weeks |
| AC-005 (Operations) | Platform Lead | Go-Live - 3 days |
| AC-006 (Business) | CDO | Go-Live day |
| AC-007 (Decommission) | CTO | Go-Live + 90 days |
