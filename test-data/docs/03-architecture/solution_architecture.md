# Solution Architecture

## Project ATLAS — Target Platform Architecture

### Architecture Principles

| Principle | Rationale |
|-----------|-----------|
| Open formats only | No proprietary storage formats; Iceberg/Parquet ensure portability |
| Separation of storage and compute | Independent scaling, cost optimisation |
| Infrastructure as Code | 100% reproducible environments via Terraform |
| Zero-trust security | Least-privilege IAM, encrypt everything, verify always |
| Observable by default | Every component emits metrics, logs, and traces |
| Immutable data | Bronze layer is append-only; mutations tracked via SCD/Iceberg snapshots |

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CONSUMERS                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Tableau  │  │ Risk Eng │  │ AxiomSL  │  │ Superset │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       └──────────────┴──────────────┴──────────────┘                    │
│                          │ JDBC/ODBC                                     │
│                    ┌─────┴─────┐                                        │
│                    │   TRINO   │  (Federated Query Engine)              │
│                    └─────┬─────┘                                        │
├──────────────────────────┼──────────────────────────────────────────────┤
│                   LAKEHOUSE (Iceberg on S3)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │    GOLD      │  │    SILVER    │  │    BRONZE    │                 │
│  │ (Business)   │  │  (Cleansed)  │  │   (Raw)      │                 │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 │
│         │                  │                  │                          │
│         └─── dbt Core ─────┘                  │                          │
│                                               │                          │
├───────────────────────────────────────────────┼──────────────────────────┤
│                    ORCHESTRATION               │                          │
│              ┌─────────────────┐              │                          │
│              │ Apache Airflow  │              │                          │
│              │   (MWAA)        │              │                          │
│              └────────┬────────┘              │                          │
│                       │ triggers              │                          │
├───────────────────────┼───────────────────────┼──────────────────────────┤
│                 INGESTION                     │                          │
│  ┌──────────────┐  ┌──────────────┐         │                          │
│  │ Spark (EMR   │  │    Kafka     │─────────┘                          │
│  │  Serverless) │  │  (MSK)       │                                    │
│  └──────┬───────┘  └──────┬───────┘                                    │
│         │                  │                                             │
├─────────┼──────────────────┼─────────────────────────────────────────────┤
│         │    SOURCE SYSTEMS │                                             │
│  ┌──────┴───┐  ┌──────────┴──┐  ┌──────────┐  ┌──────────┐           │
│  │ T24 (CDC)│  │ Payments    │  │ Reuters  │  │ KYC/AML  │           │
│  └──────────┘  └─────────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Inventory

| Component | AWS Service | Version | Purpose |
|-----------|------------|---------|---------|
| Object Storage | S3 | - | Iceberg table data (Parquet) |
| Table Format | Apache Iceberg | 1.5 | ACID transactions, time travel, schema evolution |
| Catalog | AWS Glue Data Catalog | - | Iceberg metadata, Hive Metastore compatible |
| Batch Compute | EMR Serverless | Spark 3.5 | Large-scale ingestion and backfill |
| Stream Processing | MSK (Kafka) | 3.7 | Real-time event streaming |
| CDC | Debezium (on MSK Connect) | 2.5 | Oracle → Kafka change capture |
| Transformation | dbt Core | 1.8 | SQL transformations (Silver → Gold) |
| Orchestration | MWAA (Airflow) | 2.9 | DAG scheduling and monitoring |
| Query Engine | Trino (EMR) | 450 | Federated analytical queries |
| Data Quality | Great Expectations | 0.18 | Automated data validation |
| Metadata | OpenMetadata | 1.4 | Catalog, lineage, glossary |
| Secrets | AWS Secrets Manager | - | Connection strings, API keys |
| IAM | AWS IAM + Lake Formation | - | Fine-grained access control |
| Monitoring | CloudWatch + Grafana | - | Metrics, logs, dashboards |
| CI/CD | GitHub Actions | - | Build, test, deploy automation |
| IaC | Terraform | 1.7 | Infrastructure provisioning |

### Network Architecture

- **VPC**: 10.0.0.0/16 (eu-west-2)
- **Private Subnets**: 3 AZs (compute, data, management)
- **No public subnets** — all access via VPN / PrivateLink
- **VPC Endpoints**: S3, Glue, Secrets Manager, CloudWatch, KMS
- **Transit Gateway**: Connects to on-premise DC (T24, Oracle during migration)

### Data Flow Architecture

1. **CDC Path** (near-real-time): T24 → Debezium → MSK → Spark Structured Streaming → Bronze (Iceberg)
2. **Batch Path** (daily): Source → Spark Batch (EMR Serverless) → Bronze (Iceberg)
3. **Transform Path**: Bronze → dbt (Silver) → dbt (Gold) → Iceberg tables
4. **Serve Path**: Gold tables → Trino → JDBC → Consumers
5. **Quality Path**: Each layer transition triggers Great Expectations validation

### Disaster Recovery

| Tier | RTO | RPO | Strategy |
|------|-----|-----|----------|
| Gold (Reports) | 4 hours | 1 hour | Cross-region S3 replication (eu-west-1) |
| Silver | 8 hours | 4 hours | Re-run dbt from Bronze |
| Bronze | 12 hours | 24 hours | Re-ingest from source (CDC replay from Kafka retention) |
| Infrastructure | 2 hours | N/A | Terraform apply in DR region |
