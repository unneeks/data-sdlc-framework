# Release Plan — Project ATLAS

## Release Strategy

Project ATLAS follows a **domain-by-domain phased release**, migrating one data domain at a time to reduce blast radius and allow learning between waves.

### Release Waves

| Wave | Domain | Target Date | Dependencies |
|------|--------|-------------|--------------|
| 1 | Customer & Accounts | 2026-06-01 | Core platform ready, CDC pipelines live |
| 2 | Transactions & Payments | 2026-07-15 | Wave 1 stable, streaming validated |
| 3 | Risk & Exposure | 2026-09-01 | Wave 2 stable, Risk Engine integration |
| 4 | Counterparty & KYC | 2026-10-01 | Wave 3 stable, API integrations |
| 5 | Market Data | 2026-11-01 | Wave 4 stable, real-time feed |
| 6 | Regulatory Reporting | 2026-12-15 | All domains live, full reconciliation pass |

### Release Types

| Type | Scope | Approval | Deployment |
|------|-------|----------|------------|
| Domain go-live | New domain cutover from Oracle | CAB + Compliance + Data Owner | Blue-green |
| Platform update | Infrastructure, Airflow DAGs, Spark config | Tech Lead + SRE | Rolling |
| Hotfix | P1/P2 defect in production | Tech Lead (emergency CAB if data-impacting) | Direct patch |
| dbt model change | Transform logic, new/modified models | PR review + dbt CI pass | Merge to main |

## Go-Live Checklist (per domain)

- [ ] 10-day reconciliation pass achieved
- [ ] Performance targets met in staging
- [ ] Security scan clear (Prowler + Checkov)
- [ ] Runbooks documented in Confluence
- [ ] Monitoring dashboards configured (Grafana + CloudWatch)
- [ ] Rollback procedure tested
- [ ] Data Owner sign-off obtained
- [ ] Compliance sign-off obtained (regulatory domains only)
- [ ] CAB approval granted
- [ ] Communication sent to downstream consumers (48h notice)

## Rollback Strategy

| Scenario | Action | RTO |
|----------|--------|-----|
| Data corruption detected | Iceberg time-travel to last known-good snapshot | < 30 minutes |
| Pipeline regression | Revert Airflow DAG version, replay from checkpoint | < 1 hour |
| Platform instability | Route traffic back to Oracle (DNS flip) | < 15 minutes |
| dbt model defect | Revert PR, re-run dbt from last passing state | < 45 minutes |

During dual-run, Oracle remains the primary system of record. Consumers can be rerouted within 15 minutes via connection-string update (managed by HAProxy).

## Change Advisory Board (CAB)

| Member | Role | Responsibility |
|--------|------|----------------|
| R. Chen | Platform Lead | Technical readiness |
| D. Morrison | CTO | Strategic go/no-go |
| S. Okafor | Head of Compliance | Regulatory sign-off |
| L. Peters | SRE Lead | Operational readiness |
| Domain Data Owner | Varies by wave | Data accuracy acceptance |

CAB meets weekly (Tuesday 10:00 UTC) during active release waves.

## Communication Plan

| Audience | Channel | Timing |
|----------|---------|--------|
| Downstream consumers | Email + Slack #atlas-releases | 48h before go-live |
| Analytics team | Slack #analytics + Confluence page | 1 week before |
| Senior leadership | Email summary | Same day |
| All staff (major milestones) | Company newsletter | Post go-live |
