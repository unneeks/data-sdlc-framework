# Project ATLAS: Banking Data Platform Migration

## Overview

**Project ATLAS** (Automated Transformation of Legacy Analytics Systems) migrates Meridian Bank's legacy Oracle Data Warehouse to a modern open-source lakehouse architecture on AWS.

| Attribute | Value |
|-----------|-------|
| **Programme** | Data Platform Modernisation |
| **Project ID** | PRJ-ATLAS-2026 |
| **Sponsor** | Chief Data Officer, Meridian Bank |
| **Domain** | Financial Services (Retail & Commercial Banking) |
| **Baseline Risk** | HIGH |
| **Delivery Type** | DATA_PLATFORM_MIGRATION |

## Scope

Migrate 6 core data domains from Oracle DWH (v19c) to an AWS-based lakehouse:

- **Customer Accounts** — 45M+ retail/commercial accounts
- **Transactions** — 2B+ records/year, real-time and batch
- **Risk Scores** — Credit, market, and operational risk models
- **Regulatory Reports** — Basel III/IV, IFRS 9, PRA returns
- **FX Rates** — Real-time market data feeds
- **Counterparty Data** — 500K+ institutional counterparties

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Ingestion | Apache Spark 3.5, Kafka Connect | Batch & streaming data loading |
| Storage | Apache Iceberg on S3 | ACID lakehouse tables |
| Transformation | dbt Core 1.8 | SQL-based data modelling |
| Orchestration | Apache Airflow 2.9 | Workflow scheduling & monitoring |
| Quality | Great Expectations 0.18 | Data validation & profiling |
| Governance | OpenMetadata 1.4 | Catalog, lineage, glossary |
| Serving | Trino 450 | Federated SQL query engine |
| Visualisation | Apache Superset 4.0 | BI & reporting dashboards |
| Infrastructure | Terraform 1.7, Helm 3 | IaC & container orchestration |
| CI/CD | GitHub Actions | Automated build, test, deploy |

## Repository Structure

```
.
├── docs/                    # Delivery & project documentation (per phase)
├── code/                    # All application/pipeline code
├── infrastructure/          # Terraform, Helm, Docker
├── ci-cd/                   # GitHub Actions workflows & scripts
└── config/                  # Environment-specific configuration
```

See [docs/](docs/) for phase-by-phase delivery documentation.
See [code/](code/) for all technical implementation.

## Delivery Phases

| # | Phase | Status | Gate |
|---|-------|--------|------|
| 1 | Discovery | COMPLETED | Business Case Approved |
| 2 | Requirements | COMPLETED | Requirements Sign-off |
| 3 | Architecture | COMPLETED | Architecture Review Board |
| 4 | Design | COMPLETED | Design Authority Approval |
| 5 | Development | COMPLETED | Code Complete |
| 6 | Testing | COMPLETED | Test Exit Criteria Met |
| 7 | Release | COMPLETED | Release Readiness Gate |
| 8 | Deployment | COMPLETED | Go-Live Approval |
| 9 | Operations | IN_PROGRESS | Operational Stability |
| 10 | Transition to BAU | NOT_STARTED | BAU Handover Complete |

## Key Contacts

| Role | Name | Team |
|------|------|------|
| Delivery Lead | A. Richardson | Platform Engineering |
| Data Architect | S. Patel | Data Architecture |
| Solution Architect | M. Chen | Enterprise Architecture |
| Security Lead | J. O'Brien | InfoSec |
| Business Analyst | L. Thompson | Data Strategy |
| QA Lead | R. Williams | Quality Engineering |

## Compliance & Regulatory

This project operates under:
- FCA SYSC 15A (Operational Resilience)
- PRA SS1/21 (Outsourcing & Third-Party Risk)
- GDPR / UK DPA 2018
- Basel III/IV Capital Requirements
- IFRS 9 Financial Instruments
- SOX IT General Controls
