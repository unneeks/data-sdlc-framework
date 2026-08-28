# Deployment Guide — Project ATLAS

## Deployment Architecture

All infrastructure is managed via Terraform and deployed through GitHub Actions CI/CD pipelines. Application code (Spark jobs, dbt models, Airflow DAGs) follows a GitOps model.

### Environments

| Environment | AWS Account | Region | Deployment Method |
|-------------|-------------|--------|-------------------|
| Dev | 111222333444 | eu-west-2 | Auto-deploy on merge to `develop` |
| Staging | 555666777888 | eu-west-2 | Auto-deploy on merge to `release/*` |
| Production | 999000111222 | eu-west-2 (primary), eu-west-1 (DR) | Manual approval gate |

## CI/CD Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Commit  │───►│  Build   │───►│  Test    │───►│  Deploy  │───►│ Validate │
│          │    │          │    │          │    │ (Staging)│    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                       │
                                                       ▼ (manual gate)
                                                ┌──────────┐
                                                │  Deploy  │
                                                │  (Prod)  │
                                                └──────────┘
```

### Pipeline Steps

| Step | Tool | Duration | Failure Action |
|------|------|----------|----------------|
| Lint & static analysis | ruff, sqlfluff, tflint | ~2 min | Block PR |
| Unit tests | pytest (PySpark), dbt test | ~5 min | Block PR |
| Terraform plan | Terraform 1.7 | ~3 min | Block PR (if drift detected) |
| Build Spark JARs/wheels | uv build | ~2 min | Block PR |
| Deploy to staging | Terraform apply + DAG sync | ~10 min | Alert #atlas-ci |
| Integration tests | Airflow test DAGs + GE | ~30 min | Block release |
| Production deploy | Terraform apply + DAG sync | ~10 min | Rollback on health check fail |

## Infrastructure Components

### Terraform Modules

```
infrastructure/terraform/
├── modules/
│   ├── networking/        # VPC, subnets, security groups
│   ├── storage/           # S3 buckets, lifecycle policies, KMS
│   ├── compute/           # EMR Serverless applications
│   ├── orchestration/     # MWAA environment
│   ├── streaming/         # MSK cluster, topics, connectors
│   ├── serving/           # Trino cluster (EKS-based)
│   ├── monitoring/        # CloudWatch, Grafana, alerting
│   └── security/          # IAM roles, policies, secrets
├── environments/
│   ├── dev.tfvars
│   ├── staging.tfvars
│   └── prod.tfvars
└── main.tf
```

### Key Configuration

| Component | Prod Spec | Scaling |
|-----------|-----------|---------|
| EMR Serverless | Spark 3.5, max 200 vCPU | Auto (per-job) |
| MSK | 3 brokers, m5.2xlarge, 1TB/broker | Manual (broker add) |
| MWAA | mw1.large, 5 workers max | Auto (task queue) |
| Trino (EKS) | 1 coordinator + 2-8 workers (r6g.2xlarge) | HPA on query queue |
| S3 | Unlimited | N/A |

## Deployment Procedures

### Standard Deployment (dbt models / DAGs)

```bash
# Merge PR to main triggers:
# 1. dbt compile + test in staging
# 2. Sync DAGs to staging MWAA S3 bucket
# 3. Run integration test DAG
# 4. On pass → sync to prod MWAA S3 bucket
```

### Infrastructure Change

```bash
# 1. Create PR with Terraform changes
# 2. CI runs `terraform plan` — output posted to PR
# 3. Reviewer approves plan
# 4. Merge triggers `terraform apply` to staging
# 5. Validate in staging (manual or automated)
# 6. Manual approval gate for production apply
```

### Emergency Hotfix

```bash
# 1. Branch from main: hotfix/ATLAS-XXX
# 2. Fix + unit test
# 3. Fast-track PR (single reviewer, skip integration)
# 4. Deploy direct to prod with CAB emergency approval
# 5. Backport to develop branch
```

## Health Checks (Post-Deploy)

| Check | Target | Timeout |
|-------|--------|---------|
| Airflow webserver responds | HTTP 200 on /health | 60s |
| Trino coordinator accepts queries | SELECT 1 returns | 30s |
| Kafka consumer lag | < 1000 messages on critical topics | 5 min |
| dbt source freshness | All sources within SLA | 10 min |
| CloudWatch alarms | No ALARM state on critical metrics | Immediate |

If any health check fails within 15 minutes of deploy, automatic rollback is triggered.

## Secrets Management

| Secret Type | Storage | Rotation |
|-------------|---------|----------|
| Database credentials | AWS Secrets Manager | 90 days (automated) |
| API keys (source systems) | AWS Secrets Manager | 180 days |
| Terraform state encryption | KMS (CMK) | Annual |
| Service accounts | IAM roles (no long-lived keys) | N/A |
| Kafka client certs | ACM Private CA | 365 days |
