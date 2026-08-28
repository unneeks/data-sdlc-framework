# Integration Architecture

## Source System Integration

### CDC from Core Banking (T24)

```
T24 Oracle → Debezium Connector (MSK Connect) → MSK Topic → Spark Structured Streaming → Bronze
```

- **Connector**: Debezium Oracle connector v2.5
- **Mode**: Log-based CDC (Oracle LogMiner)
- **Topics**: `cdc.t24.{schema}.{table}` (one topic per table)
- **Serialisation**: Avro with Schema Registry
- **Guarantees**: At-least-once delivery (dedup in Silver layer)

### Payments Integration

```
SWIFT/FPS/BACS → MQ Series → Kafka Bridge → MSK Topic → Spark Streaming → Bronze
```

- **Protocol**: IBM MQ → Kafka Source Connector
- **Topics**: `payments.{channel}.events`
- **Volume**: 8M messages/day peak
- **Ordering**: Partition by account_id (preserves per-account ordering)

### Market Data (FX Rates)

```
Reuters Elektron → Kafka Producer (custom) → MSK → Spark Streaming → Bronze
```

- **Protocol**: RSSL (Reuters SSL) → Custom Java adapter → Kafka
- **Topics**: `market-data.fx.{currency_pair}`
- **Latency**: < 500ms from tick to Kafka
- **EOD Snapshot**: Separate batch job at 17:00 UTC

### Downstream System Integration

| Consumer | Current (Oracle) | Target (Lakehouse) | Migration Method |
|----------|-----------------|-------------------|------------------|
| Risk Engine | JDBC to Oracle | JDBC to Trino | Connection string swap |
| AxiomSL | CSV file extract | Iceberg table read (Spark) | New adapter module |
| SAP GL | Oracle DB Link | Trino JDBC → SAP | Gateway service |
| Tableau | ODBC to Oracle | ODBC to Trino | Driver + DSN update |
| AML System | JDBC to Oracle | JDBC to Trino | Connection string swap |

### API Layer

For systems that cannot consume directly from Trino:

```yaml
# Data API (FastAPI)
endpoints:
  - GET  /api/v1/customers/{id}           # Single customer lookup
  - GET  /api/v1/transactions?account={id} # Transaction history
  - GET  /api/v1/risk-scores/{customer_id} # Latest risk scores
  - POST /api/v1/reports/generate          # Trigger report generation

# Served via API Gateway + Lambda (for low-volume lookups)
# High-volume remains direct Trino JDBC
```

### Event-Driven Integration

```yaml
# EventBridge rules for downstream notifications
events:
  - source: atlas.ingestion
    detail-type: BatchComplete
    targets: [quality-check-lambda, monitoring-dashboard]
    
  - source: atlas.quality
    detail-type: QualityFailure
    targets: [pagerduty-integration, quarantine-workflow]
    
  - source: atlas.transformation
    detail-type: GoldLayerRefreshed
    targets: [downstream-notify-sns, metadata-lineage-update]
```

### Authentication & Authorisation

| Integration Point | Auth Method | Credential Storage |
|-------------------|------------|-------------------|
| T24 CDC | Service account (Oracle) | AWS Secrets Manager |
| Kafka (MSK) | IAM authentication | IAM role |
| Trino (consumers) | LDAP + Okta SSO | IAM Identity Center |
| S3 (Iceberg) | IAM roles (Lake Formation) | Instance profiles |
| OpenMetadata | OAuth 2.0 (Okta) | OIDC configuration |
| Grafana | OAuth 2.0 (Okta) | OIDC configuration |

### Network Connectivity

| Source/Target | Protocol | Network Path |
|---------------|----------|-------------|
| T24 (on-prem) → MSK | TCP/1521 (Oracle), TCP/9092 (Kafka) | Transit Gateway |
| MSK → EMR | TCP/9092 | VPC internal (private subnet) |
| EMR → S3 | HTTPS/443 | VPC Endpoint (gateway) |
| Trino → S3 | HTTPS/443 | VPC Endpoint (gateway) |
| Tableau (corporate) → Trino | TCP/8080 | PrivateLink |
| GitHub Actions → AWS | HTTPS/443 | OIDC federation (no long-lived keys) |
