# Functional Requirements

## Project ATLAS — Data Platform Migration

### FR-001: Data Ingestion

| ID | Requirement | Priority | Domain |
|----|-------------|----------|--------|
| FR-001.1 | System shall ingest batch data from Core Banking (T24) via CDC within 2-hour SLA | Must | Customer, Transactions |
| FR-001.2 | System shall ingest streaming transaction events with < 5 min end-to-end latency | Must | Transactions |
| FR-001.3 | System shall ingest market data (FX rates) in real-time via Kafka | Must | FX Rates |
| FR-001.4 | System shall support schema evolution (additive columns) without pipeline failure | Must | All |
| FR-001.5 | System shall handle late-arriving data with configurable watermark (default: 24h) | Should | Transactions |
| FR-001.6 | System shall deduplicate records using business keys within ingestion window | Must | All |

### FR-002: Data Transformation

| ID | Requirement | Priority | Domain |
|----|-------------|----------|--------|
| FR-002.1 | System shall implement medallion architecture (bronze/silver/gold layers) | Must | All |
| FR-002.2 | System shall compute daily risk scores matching Oracle output (tolerance: 0.001%) | Must | Risk Scores |
| FR-002.3 | System shall generate all 47 regulatory report datasets per existing specifications | Must | Regulatory |
| FR-002.4 | System shall maintain full data lineage from source to consumption | Must | All |
| FR-002.5 | System shall support incremental processing (no full-refresh for daily runs) | Must | Transactions, Risk |
| FR-002.6 | System shall implement SCD Type 2 for customer dimension changes | Must | Customer |
| FR-002.7 | System shall support point-in-time queries (time travel) with 90-day retention | Should | All |

### FR-003: Data Quality

| ID | Requirement | Priority | Domain |
|----|-------------|----------|--------|
| FR-003.1 | System shall validate schema conformity on every ingestion batch | Must | All |
| FR-003.2 | System shall enforce referential integrity between customer and transaction domains | Must | Customer, Transactions |
| FR-003.3 | System shall detect and quarantine records failing business rules (not drop) | Must | All |
| FR-003.4 | System shall produce daily data quality scorecards per domain | Should | All |
| FR-003.5 | System shall alert on quality threshold breaches within 15 minutes | Must | All |
| FR-003.6 | System shall reconcile source vs target row counts and checksums daily | Must | All |

### FR-004: Data Serving

| ID | Requirement | Priority | Domain |
|----|-------------|----------|--------|
| FR-004.1 | System shall serve analytical queries via SQL interface (ANSI SQL compliant) | Must | All |
| FR-004.2 | System shall support concurrent queries from 200+ users without degradation | Must | All |
| FR-004.3 | System shall provide JDBC/ODBC connectivity for downstream systems | Must | All |
| FR-004.4 | System shall support row-level security based on user department | Must | Customer, Risk |
| FR-004.5 | System shall expose curated datasets as data products with published contracts | Should | All |

### FR-005: Data Governance

| ID | Requirement | Priority | Domain |
|----|-------------|----------|--------|
| FR-005.1 | System shall maintain a searchable data catalog with business descriptions | Must | All |
| FR-005.2 | System shall classify PII columns and enforce access policies | Must | Customer |
| FR-005.3 | System shall produce automated lineage graphs (column-level) | Must | All |
| FR-005.4 | System shall support data ownership assignment and stewardship workflows | Should | All |
| FR-005.5 | System shall maintain a business glossary linked to physical assets | Should | All |

### FR-006: Regulatory Compliance

| ID | Requirement | Priority | Domain |
|----|-------------|----------|--------|
| FR-006.1 | System shall produce Basel III capital adequacy reports per PRA schedule | Must | Regulatory |
| FR-006.2 | System shall produce IFRS 9 expected credit loss calculations | Must | Risk, Regulatory |
| FR-006.3 | System shall maintain full audit trail of data transformations | Must | All |
| FR-006.4 | System shall support regulatory data lineage queries ("where did this number come from?") | Must | Regulatory |
| FR-006.5 | System shall retain regulatory data for minimum 10 years (immutable) | Must | Regulatory |

### Traceability Matrix

| Requirement Group | Business Case Objective | Stakeholder |
|-------------------|------------------------|-------------|
| FR-001 (Ingestion) | Real-time capability, scalability | CTO, Platform Eng |
| FR-002 (Transformation) | Regulatory agility, cost reduction | Head of Risk, Reg Reporting |
| FR-003 (Quality) | Regulatory compliance, operational excellence | DPO, Internal Audit |
| FR-004 (Serving) | User experience, performance | Business Analysts, BI Team |
| FR-005 (Governance) | Compliance, data literacy | CDO, Data Stewards |
| FR-006 (Regulatory) | Regulatory compliance | Compliance, PRA/FCA |
