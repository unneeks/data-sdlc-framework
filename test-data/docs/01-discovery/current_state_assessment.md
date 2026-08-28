# Current State Assessment

## Platform Inventory

### Oracle Data Warehouse (Primary)
- **Version**: Oracle 19c Enterprise Edition (RAC, Partitioning, Advanced Analytics)
- **Hardware**: 2x Exadata X8M-2 (Full Rack), hosted in Meridian DC1
- **Storage**: 480 TB raw (320 TB usable after mirroring)
- **Current Utilisation**: 95% storage, 78% average CPU (peaks to 100% during batch)
- **Schemas**: 42 schemas across 6 business domains
- **Tables**: 3,847 tables (1,204 actively queried)
- **Views**: 2,156 materialised views (refresh schedules: 15-min to daily)

### ETL Platform
- **Tool**: Informatica PowerCenter 10.5
- **Mappings**: 1,247 production mappings
- **Workflows**: 389 workflows (batch scheduling)
- **Sessions/Day**: ~2,400 session runs
- **Batch Window**: 23:00-06:00 (frequently overruns to 07:30)
- **Known Issues**: 47 open defects, 12 classified as "accepted risk"

### Data Volumes

| Domain | Tables | Rows (Total) | Daily Increment | Retention |
|--------|--------|-------------|-----------------|-----------|
| Customer Accounts | 156 | 45M | 50K | Indefinite |
| Transactions | 312 | 2.1B | 8M | 7 years |
| Risk Scores | 89 | 890M | 2M | 5 years |
| Regulatory Reports | 67 | 120M | 500K | 10 years |
| FX Rates | 23 | 45M | 200K | 3 years |
| Counterparty | 48 | 12M | 5K | Indefinite |

### Downstream Consumers

| System | Protocol | Queries/Day | SLA |
|--------|----------|-------------|-----|
| Risk Engine (Moody's) | JDBC | 450 | < 30s response |
| Regulatory Reporting (AxiomSL) | File extract (CSV) | 12 | By 08:00 daily |
| Finance GL (SAP) | DB Link | 200 | < 60s response |
| BI Platform (Tableau) | ODBC | 3,200 | < 10s P95 |
| Anti-Money Laundering | JDBC | 800 | < 5s response |
| Customer Analytics (SAS) | Bulk extract | 6 | By 06:00 daily |

### Source System Feeds

| Source | Protocol | Frequency | Volume/Day |
|--------|----------|-----------|-----------|
| Core Banking (Temenos T24) | CDC (Oracle GoldenGate) | Real-time | 12M events |
| Payments (SWIFT/FPS) | MQ → Informatica | Batch (hourly) | 3M records |
| Market Data (Reuters) | FTP → Informatica | Real-time + EOD | 500K ticks |
| CRM (Salesforce) | REST API | Hourly | 200K records |
| Risk Models (Internal) | File drop (Parquet) | Daily | 2M records |
| Regulatory Reference | SFTP | Weekly | 50K records |

### Technical Debt Register

| ID | Description | Impact | Age |
|----|-------------|--------|-----|
| TD-001 | Undocumented business logic in PL/SQL packages (380+ packages) | Cannot validate correctness of migration | 8 years |
| TD-002 | Circular dependencies between 23 materialised views | Prevents incremental refresh optimisation | 5 years |
| TD-003 | Hardcoded database links to 4 decommissioned systems | Nightly job failures (suppressed by ops) | 3 years |
| TD-004 | No automated tests for any ETL mapping | Zero regression safety net | 12 years |
| TD-005 | 156 tables with no primary key defined | Cannot implement CDC accurately | 10 years |
| TD-006 | Mixed encoding (UTF-8, Latin-1, Windows-1252) in VARCHAR columns | Data corruption on certain customer names | 6 years |
| TD-007 | Batch scheduling via cron (not Informatica scheduler) for 89 jobs | No dependency tracking, frequent race conditions | 7 years |

### Operational Metrics (Last 12 Months)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Batch completion by 06:00 | 72% | 99% | RED |
| P1 incidents | 23 | < 6 | RED |
| Mean time to recover (P1) | 4.2 hours | < 1 hour | RED |
| Change success rate | 84% | > 95% | AMBER |
| Data quality score (DQ framework) | 76% | > 95% | RED |
| Platform availability | 99.2% | 99.9% | AMBER |

### Skills Assessment

| Skill | Current FTEs | Required | Gap |
|-------|-------------|----------|-----|
| Oracle DBA | 3 | 2 (decommission) | Surplus |
| Informatica Developer | 2 (was 6) | 0 (decommission) | - |
| Spark/PySpark | 1 | 4 | -3 |
| dbt | 0 | 3 | -3 |
| Airflow | 1 | 2 | -1 |
| Terraform/IaC | 2 | 3 | -1 |
| Data Architecture | 1 | 2 | -1 |

### Conclusion

The current platform is end-of-life from a capacity, cost, talent, and operational perspective. Migration is not optional — it is a matter of when, not if. The Oracle licence renewal in Q1 2027 creates a hard deadline for decommissioning.
