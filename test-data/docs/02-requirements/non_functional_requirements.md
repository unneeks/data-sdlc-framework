# Non-Functional Requirements

## Project ATLAS — Data Platform Migration

### NFR-001: Performance

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001.1 | Batch ingestion throughput | > 500K records/min per source | CloudWatch metrics |
| NFR-001.2 | Streaming end-to-end latency | < 5 minutes (P99) | Kafka lag monitoring |
| NFR-001.3 | dbt model execution (full daily run) | < 90 minutes | Airflow task duration |
| NFR-001.4 | Analytical query response (P95) | < 10 seconds | Trino query log |
| NFR-001.5 | Regulatory report generation | < 30 minutes per report | Airflow DAG duration |
| NFR-001.6 | Concurrent query support | 200 simultaneous users | Load test results |

### NFR-002: Availability & Reliability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-002.1 | Platform availability | 99.9% (< 8.76h downtime/year) | AWS Health + custom checks |
| NFR-002.2 | Recovery Point Objective (RPO) | < 1 hour | Iceberg snapshot frequency |
| NFR-002.3 | Recovery Time Objective (RTO) | < 4 hours | DR drill results |
| NFR-002.4 | Data durability | 99.999999999% (11 nines) | S3 durability SLA |
| NFR-002.5 | Batch job retry (automatic) | 3 retries with exponential backoff | Airflow configuration |
| NFR-002.6 | Zero data loss for streaming | At-least-once delivery guaranteed | Kafka consumer group offsets |

### NFR-003: Security

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-003.1 | Encryption at rest | AES-256 (AWS KMS CMK) | AWS Config rule |
| NFR-003.2 | Encryption in transit | TLS 1.3 minimum | Network scanner |
| NFR-003.3 | Authentication | SSO via Okta (SAML 2.0) | IAM Identity Center |
| NFR-003.4 | Authorisation granularity | Column-level (PII masking) | Trino access control |
| NFR-003.5 | Secrets management | No secrets in code or config files | HashiCorp Vault + AWS Secrets Manager |
| NFR-003.6 | Vulnerability scanning | Zero critical/high findings in prod | Snyk + AWS Inspector |
| NFR-003.7 | Audit logging | All data access logged, retained 2 years | CloudTrail + S3 access logs |

### NFR-004: Scalability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-004.1 | Storage growth accommodation | 10x current volume without re-architecture | S3 unlimited + Iceberg partitioning |
| NFR-004.2 | Compute elasticity | Auto-scale 2x-10x based on workload | EMR Serverless scaling |
| NFR-004.3 | New domain onboarding | < 2 weeks from schema to serving | Onboarding checklist completion |
| NFR-004.4 | Concurrent pipeline support | 50+ simultaneous DAGs without resource contention | Airflow worker pool metrics |

### NFR-005: Maintainability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-005.1 | Code test coverage | > 80% for all transformation logic | pytest + dbt test counts |
| NFR-005.2 | Documentation coverage | All tables have descriptions in catalog | OpenMetadata completeness score |
| NFR-005.3 | Mean time to onboard new developer | < 5 days to first PR merged | Onboarding survey |
| NFR-005.4 | Deployment frequency | Multiple deploys per day (CI/CD) | GitHub Actions metrics |
| NFR-005.5 | Change failure rate | < 5% of deployments cause rollback | Incident correlation |

### NFR-006: Compliance

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-006.1 | Data residency | All data stored in eu-west-2 (London) | AWS Config rule |
| NFR-006.2 | Right to erasure (GDPR Article 17) | Deletion within 30 days of request | Erasure workflow SLA |
| NFR-006.3 | Data retention enforcement | Automated lifecycle policies per domain | Iceberg table maintenance |
| NFR-006.4 | SOX ITGC compliance | Segregation of duties, change management | Audit evidence pack |
| NFR-006.5 | PCI DSS (card data) | Tokenisation before lakehouse ingestion | Data flow audit |

### NFR-007: Observability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-007.1 | Pipeline monitoring | Real-time DAG/task status dashboard | Airflow UI + Grafana |
| NFR-007.2 | Alerting response time | P1 alert to human acknowledgement < 15 min | PagerDuty metrics |
| NFR-007.3 | Log retention | 90 days hot, 1 year cold | CloudWatch + S3 Glacier |
| NFR-007.4 | Distributed tracing | End-to-end trace from source to serving | OpenTelemetry + Jaeger |
| NFR-007.5 | Cost observability | Daily cost attribution by domain/team | AWS Cost Explorer tags |
