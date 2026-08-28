# Logical Data Model — Project ATLAS

## Overview

This document defines the logical data model for Meridian Bank's lakehouse migration, covering all 6 core data domains.

## Domain Model

### 1. Customer Accounts Domain

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| Customer | A natural or legal person holding accounts | customer_id, customer_type, kyc_status, risk_tier |
| Account | A financial product instance | account_id, account_type, currency, status, opened_date |
| AccountHolder | Junction: customer ↔ account (supports joint) | customer_id, account_id, relationship_type |
| Address | Physical/mailing addresses | address_id, address_type, country_code |

### 2. Transactions Domain

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| Transaction | A financial movement event | txn_id, txn_type, amount, currency, timestamp, status |
| TransactionParty | Sender or receiver | party_id, party_type, account_ref, bic_code |
| TransactionClassification | AML/fraud classification | classification_id, category, confidence_score |

### 3. Risk Scores Domain

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| CreditRiskScore | PD/LGD/EAD model outputs | score_id, customer_id, pd, lgd, ead, model_version |
| MarketRiskExposure | VaR and stress test results | exposure_id, portfolio_id, var_95, var_99, stress_scenario |
| OperationalRiskEvent | Loss event records | event_id, category, loss_amount, root_cause |

### 4. Regulatory Reporting Domain

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| RegulatoryReturn | A filed regulatory report | return_id, regime, period, status, submission_date |
| CapitalRequirement | Basel III/IV capital calc | requirement_id, tier, amount, rwa |
| IFRS9Provision | Expected credit loss | provision_id, stage, ecl_amount, portfolio |

### 5. FX Rates Domain

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| FXRate | Point-in-time exchange rate | rate_id, base_ccy, quote_ccy, mid_rate, timestamp |
| FXForwardCurve | Term structure | curve_id, tenor, forward_rate, valuation_date |

### 6. Counterparty Domain

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| Counterparty | External institution | counterparty_id, legal_name, lei, country, sector |
| CreditLimit | Exposure limit per counterparty | limit_id, counterparty_id, limit_amount, utilisation |
| NettingAgreement | ISDA/CSA master agreements | agreement_id, agreement_type, effective_date |

## Relationships

```
Customer --[1:N]--> Account
Customer --[1:N]--> CreditRiskScore
Account --[1:N]--> Transaction
Transaction --[1:N]--> TransactionParty
Transaction --[0:1]--> TransactionClassification
Counterparty --[1:N]--> CreditLimit
Counterparty --[1:N]--> NettingAgreement
RegulatoryReturn --[1:N]--> CapitalRequirement
FXRate --[N:1]--> FXForwardCurve
```

## Data Classification

| Classification | Handling | Examples |
|---------------|----------|----------|
| RESTRICTED | Encrypted at rest + in transit, column-level access | PII, account numbers |
| CONFIDENTIAL | Encrypted at rest, role-based access | Risk scores, P&L |
| INTERNAL | Standard controls | Metadata, reference data |
| PUBLIC | Open access within bank | FX rates (delayed), glossary |

## Slowly Changing Dimensions

- **SCD Type 2**: Customer, Account, Counterparty (full history)
- **SCD Type 1**: FXRate (overwrite, time-series partitioned)
- **SCD Type 4**: RiskScore (separate history table)
