# Data Requirements

## Project ATLAS — Data Domain Specifications

### Domain: Customer Accounts

| Attribute | Specification |
|-----------|--------------|
| Source System | Temenos T24 Core Banking |
| Extraction Method | CDC (Debezium → Kafka) |
| Volume | 45M records, 50K new/modified daily |
| Key Fields | customer_id (PK), account_number, sort_code |
| PII Fields | full_name, date_of_birth, address, email, phone, national_insurance_number |
| SCD Type | Type 2 (full history) |
| Retention | Indefinite (regulatory) |
| Quality Rules | NOT NULL on PK, valid sort_code format, age 18-120 |

### Domain: Transactions

| Attribute | Specification |
|-----------|--------------|
| Source System | Payments Hub (SWIFT, FPS, BACS, CHAPS) |
| Extraction Method | Streaming (Kafka) + daily batch reconciliation |
| Volume | 2.1B records total, 8M daily |
| Key Fields | transaction_id (PK), account_id (FK), timestamp |
| Sensitive Fields | amount, counterparty_account, reference |
| Partitioning | By transaction_date (daily) |
| Retention | 7 years (FCA requirement) |
| Quality Rules | amount > 0, valid currency code (ISO 4217), referential integrity to accounts |

### Domain: Risk Scores

| Attribute | Specification |
|-----------|--------------|
| Source System | Internal Risk Engine (Python/SAS models) |
| Extraction Method | File drop (Parquet, daily) |
| Volume | 890M records, 2M daily recalculations |
| Key Fields | risk_score_id, customer_id (FK), model_id, score_date |
| Model Types | PD (Probability of Default), LGD (Loss Given Default), EAD (Exposure at Default) |
| Precision | 6 decimal places (must match Oracle output to 0.001%) |
| Retention | 5 years |
| Quality Rules | Score range [0.0, 1.0], model_id in reference list, no future dates |

### Domain: Regulatory Reports

| Attribute | Specification |
|-----------|--------------|
| Source System | Derived (transformation layer) |
| Report Types | COREP, FINREP, Large Exposures, Liquidity (LCR/NSFR) |
| Submission Frequency | Monthly (some quarterly) |
| Format | XBRL taxonomy + internal CSV |
| Immutability | Once submitted, data is append-only (no updates) |
| Retention | 10 years (PRA requirement) |
| Quality Rules | Cross-validation between reports, balance sheet reconciliation |

### Domain: FX Rates

| Attribute | Specification |
|-----------|--------------|
| Source System | Reuters Elektron / Refinitiv |
| Extraction Method | Real-time streaming (Kafka) + EOD snapshot |
| Volume | 45M records, 200K daily ticks |
| Key Fields | currency_pair, timestamp, rate_type (bid/ask/mid) |
| Precision | 8 decimal places |
| Retention | 3 years |
| Quality Rules | Rate within 50% of previous close, no gaps > 5min during market hours |

### Domain: Counterparty Data

| Attribute | Specification |
|-----------|--------------|
| Source System | KYC/AML Platform + LEI Registry |
| Extraction Method | REST API (hourly delta) |
| Volume | 12M records, 5K modifications daily |
| Key Fields | counterparty_id (PK), lei_code, jurisdiction |
| Sensitive Fields | beneficial_owners, sanctions_status |
| Retention | Indefinite |
| Quality Rules | Valid LEI format (ISO 17442), jurisdiction in ISO 3166, sanctions check non-null |

### Data Lineage Requirements

All data must maintain lineage from source to consumption:

```
Source System → Ingestion (Bronze) → Cleansed (Silver) → Business (Gold) → Report/Dashboard
```

Each transformation step must record:
- Input dataset(s) and version
- Transformation logic reference (dbt model / Spark job)
- Output dataset and version
- Execution timestamp
- Row counts (in/out/rejected)

### Data Classification

| Classification | Description | Controls |
|----------------|-------------|----------|
| RESTRICTED | PII, financial secrets | Encryption, masking, audit, MFA access |
| CONFIDENTIAL | Internal business data | Encryption, role-based access |
| INTERNAL | Operational metrics | Standard access controls |
| PUBLIC | Reference data (FX rates, LEIs) | No special controls |
