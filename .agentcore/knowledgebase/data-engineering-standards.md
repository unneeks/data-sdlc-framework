# Data Engineering Standards

## Naming Conventions
- Table names: snake_case, prefixed by domain (e.g., `finance_transactions`)
- Column names: snake_case, no abbreviations
- Pipeline names: kebab-case with stage suffix (e.g., `ingest-raw-to-bronze`)

## Quality Requirements
- Every data asset must have at least one freshness check
- Primary key uniqueness must be validated
- Null rate thresholds: < 5% for required fields
- Schema evolution must be backwards-compatible

## Delivery Gates
- All quality checks must pass before promotion
- Impact analysis required for schema changes
- Regression tests required for transformation logic changes
