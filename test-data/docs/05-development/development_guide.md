# Development Guide — Project ATLAS

## Local Development Setup

### Prerequisites

- Docker Desktop (for local Spark/Airflow/Trino/Kafka)
- Python 3.11+ with `uv` package manager
- Terraform 1.7+
- AWS CLI v2 (configured with `meridian-dev` profile)
- dbt-core 1.7+ with dbt-spark adapter

### Quick Start

```bash
# Clone and set up
git clone git@github.com:meridian-bank/project-atlas.git
cd project-atlas

# Start local infrastructure
docker compose -f infrastructure/docker/docker-compose.yml up -d

# Install Python deps
uv sync

# Run dbt against local Spark
cd code/transformation
dbt deps
dbt seed --target local
dbt run --target local
dbt test --target local

# Run a Spark job locally
cd code/ingestion/spark_jobs
spark-submit --master local[4] customer_accounts_ingestion.py --env local
```

## Environment Promotion

```
local → dev → staging → prod
```

| Environment | Purpose | Data | Infra |
|-------------|---------|------|-------|
| local | Developer laptop (Docker) | Synthetic (100 rows) | MinIO, local Spark |
| dev | Shared development | Anonymised subset (10K rows) | AWS (scaled down) |
| staging | Pre-prod validation | Production-like volume (1M rows) | AWS (prod-equivalent) |
| prod | Live production | Full production data | AWS (HA, multi-AZ) |

## Testing Pyramid

```
          ┌─────────────┐
          │  E2E Tests  │  ← Full pipeline run (staging, daily)
         ┌┴─────────────┴┐
         │ Integration    │  ← Cross-service (dbt + quality, per PR)
        ┌┴───────────────┴┐
        │  Unit Tests     │  ← PySpark transforms, dbt models (every commit)
       ┌┴─────────────────┴┐
       │  Static Analysis   │  ← Linting, type checking, secrets scan (pre-commit)
       └───────────────────┘
```

## Branching Strategy

```
main ─────────────────────────────────────────►
  │                                    ▲
  └── release/1.0 ─────────────────────┤
        │                    ▲          │
        └── feature/ING-042-cdc ───────┘
```

- Feature branches: short-lived (<3 days), squash-merged
- Release branches: cut weekly, only hotfixes after cut
- Main: always deployable, protected

## PR Checklist

- [ ] dbt models compile without errors
- [ ] All dbt tests pass
- [ ] PySpark unit tests pass (pytest)
- [ ] No secrets in code (gitleaks pre-commit)
- [ ] Terraform plan shows expected changes
- [ ] Documentation updated (schema.yml, ADRs if architectural)
- [ ] Data quality expectations updated if schema changed
