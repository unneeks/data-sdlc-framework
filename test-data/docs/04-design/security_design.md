# Security Design — Project ATLAS

## Data Classification & Encryption

| Classification | At Rest | In Transit | Column-Level | Examples |
|---------------|---------|------------|--------------|----------|
| RESTRICTED | AES-256 (KMS CMK) | TLS 1.3 | Yes (Iceberg column encryption) | PII, account numbers, balances |
| CONFIDENTIAL | AES-256 (KMS CMK) | TLS 1.3 | No | Risk scores, internal IDs |
| INTERNAL | SSE-S3 | TLS 1.2+ | No | Metadata, configs |

## Access Control

### IAM Role Hierarchy

```
meridian-atlas-admin          — Full platform admin (break-glass only)
meridian-atlas-data-engineer  — Read/write raw+staging, read curated
meridian-atlas-analyst        — Read curated marts only (via Trino)
meridian-atlas-airflow        — Service role for orchestration
meridian-atlas-spark          — Service role for Spark jobs
meridian-atlas-dbt            — Service role for transformations
```

### Lake Formation Permissions

| Principal | Database | Table | Column Filter |
|-----------|----------|-------|---------------|
| Analysts | meridian_curated | mart_* | Exclude: customer_name, account_number |
| Risk Team | meridian_curated | mart_risk_* | All columns |
| Regulatory | meridian_curated | mart_regulatory_* | All columns |
| Data Engineers | meridian_* | All | All columns |

## Network Security

- All compute in private subnets (no public IPs)
- VPC endpoints for S3, Glue, KMS, CloudWatch
- Security groups: least-privilege, no 0.0.0.0/0 ingress
- MSK (Kafka) with SASL/SCRAM + TLS
- Trino with HTTPS + LDAP/Kerberos authentication

## Secrets Management

| Secret | Store | Rotation |
|--------|-------|----------|
| Oracle CDC credentials | AWS Secrets Manager | 90 days |
| Kafka SASL passwords | AWS Secrets Manager | 90 days |
| Trino keystore | AWS Secrets Manager | Annual |
| dbt service account | IAM Role (no long-lived creds) | N/A |

## Audit & Compliance

- CloudTrail: all API calls logged, 1-year retention
- S3 access logging: all object-level operations
- Iceberg table audit columns: `_loaded_at`, `_source_system`, `_batch_id`
- Lake Formation data access audit: all query-level access
- PRA/FCA regulatory audit trail: immutable, 7-year retention
