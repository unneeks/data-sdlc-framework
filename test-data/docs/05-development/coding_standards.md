# Coding Standards — Project ATLAS

## Python (PySpark / Airflow)

- **Version**: Python 3.11+
- **Formatter**: `ruff format` (line length 100)
- **Linter**: `ruff check` with banking-specific rules enabled
- **Type hints**: Required on all function signatures
- **Docstrings**: Google style, required on public functions

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Module | snake_case | `customer_accounts_ingestion.py` |
| Class | PascalCase | `TransactionProcessor` |
| Function | snake_case | `load_daily_transactions()` |
| Constant | UPPER_SNAKE | `MAX_RETRY_ATTEMPTS = 3` |
| Spark DataFrame | df_ prefix | `df_transactions` |

### PySpark Patterns

```python
# Always use explicit schemas (never infer)
from pyspark.sql.types import StructType, StructField, StringType, DecimalType

TRANSACTION_SCHEMA = StructType([
    StructField("txn_id", StringType(), nullable=False),
    StructField("amount", DecimalType(18, 4), nullable=False),
])

# Always partition writes
df_output.writeTo("meridian_curated.transactions") \
    .partitionedBy("txn_date", "account_bucket") \
    .createOrReplace()
```

## SQL (dbt)

- **Style**: lowercase keywords, trailing commas, CTEs over subqueries
- **Naming**: `stg_` / `int_` / `mart_` prefixes mandatory
- **Testing**: Every model must have at least `unique` + `not_null` on primary key
- **Documentation**: Every model and column documented in `schema.yml`

### dbt Model Template

```sql
{{
    config(
        materialized='incremental',
        unique_key='txn_id',
        partition_by={'field': 'txn_date', 'data_type': 'date'},
        on_schema_change='append_new_columns'
    )
}}

with source as (
    select * from {{ ref('stg_transactions') }}
    {% if is_incremental() %}
    where _loaded_at > (select max(_loaded_at) from {{ this }})
    {% endif %}
),

final as (
    select
        txn_id,
        account_id,
        amount,
        currency,
        txn_timestamp,
        {{ dbt_utils.generate_surrogate_key(['txn_id']) }} as txn_surrogate_key,
    from source
)

select * from final
```

## Terraform (IaC)

- **Version**: Terraform 1.7+
- **Provider pinning**: Exact versions in `versions.tf`
- **Module naming**: `modules/{resource_type}/`
- **State**: Remote backend (S3 + DynamoDB locking)
- **Tagging**: All resources tagged with `project`, `environment`, `cost_centre`, `data_classification`

## Git Workflow

- **Branching**: `main` → `release/*` → `feature/*` / `hotfix/*`
- **Commits**: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`)
- **PR Requirements**: 2 approvals, passing CI, no secrets detected
- **Protected branches**: `main`, `release/*` — no force push
