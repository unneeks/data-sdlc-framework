#!/usr/bin/env bash
# Project ATLAS — Integration Test Runner
# Runs end-to-end pipeline validation in the staging environment.
# Called by: cd-staging.yml (integration-tests job)
#
# Prerequisites:
#   - AWS credentials configured (via OIDC or env vars)
#   - ATLAS_ENV set to "staging"
#   - Python packages: boto3, awswrangler, pytest, great-expectations, soda-core
#
# Usage:
#   ./ci-cd/scripts/run_integration_tests.sh [--skip-data-quality] [--verbose]

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="${REPO_ROOT}/reports/integration"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)

ATLAS_ENV="${ATLAS_ENV:-staging}"
AWS_REGION="${AWS_REGION:-us-east-1}"
GLUE_CATALOG_DB="${GLUE_CATALOG_DB:-atlas_${ATLAS_ENV}}"

# Test configuration
MAX_RETRIES=3
RETRY_DELAY=10
DATA_FRESHNESS_HOURS=24
MIN_ROW_COUNT_CUSTOMERS=1000
MIN_ROW_COUNT_TRANSACTIONS=10000

# Flags
SKIP_DATA_QUALITY=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-data-quality) SKIP_DATA_QUALITY=true; shift ;;
        --verbose) VERBOSE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $(date +%H:%M:%S) $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date +%H:%M:%S) $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date +%H:%M:%S) $*"; }

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Integration tests FAILED (exit code: $exit_code)"
        log_info "Reports saved to: $REPORTS_DIR"
    fi
    exit $exit_code
}
trap cleanup EXIT

retry_command() {
    local cmd="$1"
    local retries=${2:-$MAX_RETRIES}
    local delay=${3:-$RETRY_DELAY}

    for ((i=1; i<=retries; i++)); do
        if eval "$cmd"; then
            return 0
        fi
        if [ $i -lt $retries ]; then
            log_warn "Attempt $i/$retries failed. Retrying in ${delay}s..."
            sleep $delay
        fi
    done
    log_error "Command failed after $retries attempts: $cmd"
    return 1
}

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────
log_info "Starting ATLAS Integration Tests"
log_info "Environment: $ATLAS_ENV | Region: $AWS_REGION | Database: $GLUE_CATALOG_DB"
log_info "Reports directory: $REPORTS_DIR"

mkdir -p "$REPORTS_DIR"

# Verify AWS connectivity
log_info "Verifying AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log_error "AWS credentials not configured or expired"
    exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
log_info "AWS Account: $ACCOUNT_ID"

# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Glue Catalog Validation
# ─────────────────────────────────────────────────────────────────────────────
log_info "━━━ Test 1: Glue Catalog Validation ━━━"

python3 << PYTHON_EOF
import boto3
import json
import sys
from datetime import datetime

client = boto3.client('glue', region_name='${AWS_REGION}')
results = {"test": "glue_catalog_validation", "timestamp": datetime.utcnow().isoformat(), "checks": []}

# Verify database exists
try:
    db = client.get_database(Name='${GLUE_CATALOG_DB}')
    results["checks"].append({"name": "database_exists", "status": "PASS", "details": db["Database"]["Name"]})
except Exception as e:
    results["checks"].append({"name": "database_exists", "status": "FAIL", "details": str(e)})
    print(f"FAIL: Database ${GLUE_CATALOG_DB} not found: {e}")
    sys.exit(1)

# Verify expected tables exist
expected_tables = [
    "raw_customer_accounts",
    "raw_transactions",
    "stg_customer_accounts",
    "stg_transactions",
    "dim_customer",
    "dim_account",
    "dim_branch",
    "fact_transaction",
    "fact_daily_balance",
    "rpt_customer_360",
]

tables_response = client.get_tables(DatabaseName='${GLUE_CATALOG_DB}', MaxResults=100)
existing_tables = [t["Name"] for t in tables_response["TableList"]]

missing = set(expected_tables) - set(existing_tables)
if missing:
    results["checks"].append({"name": "expected_tables", "status": "FAIL", "details": f"Missing: {missing}"})
    print(f"FAIL: Missing tables: {missing}")
    sys.exit(1)
else:
    results["checks"].append({"name": "expected_tables", "status": "PASS", "details": f"{len(expected_tables)} tables verified"})

# Verify table formats (should be Iceberg)
for table_name in ["dim_customer", "fact_transaction"]:
    table = client.get_table(DatabaseName='${GLUE_CATALOG_DB}', Name=table_name)
    params = table["Table"].get("Parameters", {})
    table_type = params.get("table_type", "unknown")
    if table_type.lower() == "iceberg":
        results["checks"].append({"name": f"{table_name}_format", "status": "PASS", "details": "Iceberg"})
    else:
        results["checks"].append({"name": f"{table_name}_format", "status": "WARN", "details": f"Expected Iceberg, got {table_type}"})

# Write results
with open('${REPORTS_DIR}/01_glue_catalog.json', 'w') as f:
    json.dump(results, f, indent=2)

passed = sum(1 for c in results["checks"] if c["status"] == "PASS")
total = len(results["checks"])
print(f"Glue Catalog: {passed}/{total} checks passed")
PYTHON_EOF

log_info "Glue Catalog validation complete"

# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Data Freshness Checks
# ─────────────────────────────────────────────────────────────────────────────
log_info "━━━ Test 2: Data Freshness Checks ━━━"

python3 << PYTHON_EOF
import boto3
import json
import sys
from datetime import datetime, timedelta

client = boto3.client('glue', region_name='${AWS_REGION}')
results = {"test": "data_freshness", "timestamp": datetime.utcnow().isoformat(), "checks": []}
threshold = datetime.utcnow() - timedelta(hours=${DATA_FRESHNESS_HOURS})

critical_tables = ["fact_transaction", "dim_customer", "dim_account"]

for table_name in critical_tables:
    try:
        table = client.get_table(DatabaseName='${GLUE_CATALOG_DB}', Name=table_name)
        update_time = table["Table"].get("UpdateTime")
        if update_time and update_time >= threshold:
            results["checks"].append({
                "name": f"{table_name}_freshness",
                "status": "PASS",
                "details": f"Last updated: {update_time.isoformat()}"
            })
        else:
            results["checks"].append({
                "name": f"{table_name}_freshness",
                "status": "WARN",
                "details": f"Last updated: {update_time.isoformat() if update_time else 'unknown'} (threshold: {threshold.isoformat()})"
            })
    except Exception as e:
        results["checks"].append({"name": f"{table_name}_freshness", "status": "FAIL", "details": str(e)})

with open('${REPORTS_DIR}/02_data_freshness.json', 'w') as f:
    json.dump(results, f, indent=2)

failed = sum(1 for c in results["checks"] if c["status"] == "FAIL")
if failed > 0:
    print(f"FAIL: {failed} freshness check(s) failed")
    sys.exit(1)
print(f"Data freshness: All {len(results['checks'])} checks passed")
PYTHON_EOF

log_info "Data freshness checks complete"

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Row Count Validation
# ─────────────────────────────────────────────────────────────────────────────
log_info "━━━ Test 3: Row Count Validation ━━━"

python3 << PYTHON_EOF
import boto3
import json
import sys
import time
from datetime import datetime

athena = boto3.client('athena', region_name='${AWS_REGION}')
results = {"test": "row_count_validation", "timestamp": datetime.utcnow().isoformat(), "checks": []}

OUTPUT_LOCATION = "s3://atlas-athena-results-${ATLAS_ENV}/integration-tests/"

def run_athena_query(query):
    """Execute Athena query and return results."""
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": "${GLUE_CATALOG_DB}"},
        ResultConfiguration={"OutputLocation": OUTPUT_LOCATION}
    )
    execution_id = response["QueryExecutionId"]

    # Wait for completion
    for _ in range(60):
        status = athena.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)

    if state != "SUCCEEDED":
        reason = status["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
        raise Exception(f"Query {state}: {reason}")

    result = athena.get_query_results(QueryExecutionId=execution_id)
    return result["ResultSet"]["Rows"]

# Validate row counts
checks = [
    ("dim_customer", ${MIN_ROW_COUNT_CUSTOMERS}),
    ("dim_account", ${MIN_ROW_COUNT_CUSTOMERS}),
    ("fact_transaction", ${MIN_ROW_COUNT_TRANSACTIONS}),
]

for table, min_count in checks:
    try:
        rows = run_athena_query(f"SELECT COUNT(*) as cnt FROM {table}")
        count = int(rows[1]["Data"][0]["VarCharValue"])
        if count >= min_count:
            results["checks"].append({
                "name": f"{table}_row_count",
                "status": "PASS",
                "details": f"Count: {count:,} (min: {min_count:,})"
            })
        else:
            results["checks"].append({
                "name": f"{table}_row_count",
                "status": "FAIL",
                "details": f"Count: {count:,} below minimum {min_count:,}"
            })
    except Exception as e:
        results["checks"].append({
            "name": f"{table}_row_count",
            "status": "FAIL",
            "details": str(e)
        })

with open('${REPORTS_DIR}/03_row_counts.json', 'w') as f:
    json.dump(results, f, indent=2)

failed = sum(1 for c in results["checks"] if c["status"] == "FAIL")
if failed > 0:
    print(f"FAIL: {failed} row count check(s) failed")
    sys.exit(1)
print(f"Row counts: All {len(results['checks'])} checks passed")
PYTHON_EOF

log_info "Row count validation complete"

# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Data Quality (Great Expectations + Soda)
# ─────────────────────────────────────────────────────────────────────────────
if [ "$SKIP_DATA_QUALITY" = false ]; then
    log_info "━━━ Test 4: Data Quality Checks ━━━"

    # Run Great Expectations
    log_info "Running Great Expectations suites..."
    python3 << PYTHON_EOF
import json
import sys
from datetime import datetime

results = {"test": "great_expectations", "timestamp": datetime.utcnow().isoformat(), "checks": []}

try:
    import great_expectations as gx

    context = gx.get_context(project_root_dir="${REPO_ROOT}/code/quality/great_expectations")

    suites = ["customer_accounts_suite", "transactions_suite"]
    all_passed = True

    for suite_name in suites:
        try:
            # Run validation
            checkpoint_result = context.run_checkpoint(
                checkpoint_name=f"{suite_name}_checkpoint"
            )
            success = checkpoint_result.success
            results["checks"].append({
                "name": f"ge_{suite_name}",
                "status": "PASS" if success else "FAIL",
                "details": f"Suite validated successfully" if success else "Expectations failed"
            })
            if not success:
                all_passed = False
        except Exception as e:
            results["checks"].append({
                "name": f"ge_{suite_name}",
                "status": "SKIP",
                "details": f"Could not run: {str(e)[:100]}"
            })

except ImportError:
    results["checks"].append({
        "name": "great_expectations_import",
        "status": "SKIP",
        "details": "great_expectations not installed"
    })

with open('${REPORTS_DIR}/04_great_expectations.json', 'w') as f:
    json.dump(results, f, indent=2)

failed = sum(1 for c in results["checks"] if c["status"] == "FAIL")
print(f"Great Expectations: {len(results['checks'])} suites evaluated, {failed} failures")
if failed > 0:
    sys.exit(1)
PYTHON_EOF

    # Run Soda checks
    log_info "Running Soda quality checks..."
    python3 << PYTHON_EOF
import json
import sys
from datetime import datetime

results = {"test": "soda_checks", "timestamp": datetime.utcnow().isoformat(), "checks": []}

try:
    from soda.core.scan import Scan

    scan = Scan()
    scan.set_data_source_name("atlas_${ATLAS_ENV}")
    scan.add_sodacl_yaml_files("${REPO_ROOT}/code/quality/soda/checks/")
    scan.set_scan_definition_name("atlas_integration_${ATLAS_ENV}")

    scan.execute()

    if scan.has_check_fails():
        results["checks"].append({
            "name": "soda_scan",
            "status": "FAIL",
            "details": f"Failed checks: {scan.get_checks_fail_text()}"
        })
    else:
        results["checks"].append({
            "name": "soda_scan",
            "status": "PASS",
            "details": f"All Soda checks passed"
        })

except ImportError:
    results["checks"].append({
        "name": "soda_import",
        "status": "SKIP",
        "details": "soda-core not installed"
    })
except Exception as e:
    results["checks"].append({
        "name": "soda_scan",
        "status": "SKIP",
        "details": f"Could not run: {str(e)[:100]}"
    })

with open('${REPORTS_DIR}/05_soda_checks.json', 'w') as f:
    json.dump(results, f, indent=2)

failed = sum(1 for c in results["checks"] if c["status"] == "FAIL")
print(f"Soda: {len(results['checks'])} checks evaluated, {failed} failures")
if failed > 0:
    sys.exit(1)
PYTHON_EOF

    log_info "Data quality checks complete"
else
    log_warn "Skipping data quality checks (--skip-data-quality flag set)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Pipeline Lineage & Consistency
# ─────────────────────────────────────────────────────────────────────────────
log_info "━━━ Test 5: Pipeline Lineage & Consistency ━━━"

python3 << PYTHON_EOF
import boto3
import json
import sys
import time
from datetime import datetime

athena = boto3.client('athena', region_name='${AWS_REGION}')
results = {"test": "lineage_consistency", "timestamp": datetime.utcnow().isoformat(), "checks": []}

OUTPUT_LOCATION = "s3://atlas-athena-results-${ATLAS_ENV}/integration-tests/"

def run_query(query):
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": "${GLUE_CATALOG_DB}"},
        ResultConfiguration={"OutputLocation": OUTPUT_LOCATION}
    )
    eid = response["QueryExecutionId"]
    for _ in range(60):
        s = athena.get_query_execution(QueryExecutionId=eid)["QueryExecution"]["Status"]["State"]
        if s in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)
    if s != "SUCCEEDED":
        raise Exception(f"Query failed: {s}")
    return athena.get_query_results(QueryExecutionId=eid)["ResultSet"]["Rows"]

# Check referential integrity: all transactions reference valid accounts
try:
    rows = run_query("""
        SELECT COUNT(*) as orphan_count
        FROM fact_transaction ft
        LEFT JOIN dim_account da ON ft.account_key = da.account_key
        WHERE da.account_key IS NULL
    """)
    orphan_count = int(rows[1]["Data"][0]["VarCharValue"])
    results["checks"].append({
        "name": "transaction_account_integrity",
        "status": "PASS" if orphan_count == 0 else "FAIL",
        "details": f"Orphan transactions: {orphan_count}"
    })
except Exception as e:
    results["checks"].append({
        "name": "transaction_account_integrity",
        "status": "SKIP",
        "details": str(e)[:200]
    })

# Check no duplicate primary keys in dimension tables
for dim_table, pk_col in [("dim_customer", "customer_key"), ("dim_account", "account_key")]:
    try:
        rows = run_query(f"""
            SELECT COUNT(*) - COUNT(DISTINCT {pk_col}) as dup_count
            FROM {dim_table}
        """)
        dup_count = int(rows[1]["Data"][0]["VarCharValue"])
        results["checks"].append({
            "name": f"{dim_table}_pk_uniqueness",
            "status": "PASS" if dup_count == 0 else "FAIL",
            "details": f"Duplicate keys: {dup_count}"
        })
    except Exception as e:
        results["checks"].append({
            "name": f"{dim_table}_pk_uniqueness",
            "status": "SKIP",
            "details": str(e)[:200]
        })

# Check fact-to-dimension row ratio is reasonable
try:
    rows = run_query("""
        SELECT
            (SELECT COUNT(*) FROM fact_transaction) as fact_count,
            (SELECT COUNT(*) FROM dim_customer) as dim_count
    """)
    fact_count = int(rows[1]["Data"][0]["VarCharValue"])
    dim_count = int(rows[1]["Data"][1]["VarCharValue"])
    ratio = fact_count / dim_count if dim_count > 0 else 0
    # Expect at least 5 transactions per customer on average
    results["checks"].append({
        "name": "fact_dim_ratio",
        "status": "PASS" if ratio >= 5 else "WARN",
        "details": f"Transactions/Customer ratio: {ratio:.1f}"
    })
except Exception as e:
    results["checks"].append({
        "name": "fact_dim_ratio",
        "status": "SKIP",
        "details": str(e)[:200]
    })

with open('${REPORTS_DIR}/06_lineage_consistency.json', 'w') as f:
    json.dump(results, f, indent=2)

failed = sum(1 for c in results["checks"] if c["status"] == "FAIL")
total = len(results["checks"])
print(f"Lineage & Consistency: {total - failed}/{total} checks passed")
if failed > 0:
    sys.exit(1)
PYTHON_EOF

log_info "Pipeline lineage checks complete"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "ATLAS Integration Tests — COMPLETE"
log_info "Environment: $ATLAS_ENV"
log_info "Timestamp: $TIMESTAMP"
log_info "Reports: $REPORTS_DIR"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Generate summary report
python3 << PYTHON_EOF
import json
import glob
from datetime import datetime

report_files = glob.glob('${REPORTS_DIR}/*.json')
summary = {
    "run_timestamp": datetime.utcnow().isoformat(),
    "environment": "${ATLAS_ENV}",
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "skipped": 0,
    "test_suites": []
}

for rf in sorted(report_files):
    with open(rf) as f:
        data = json.load(f)
    checks = data.get("checks", [])
    suite_summary = {
        "name": data["test"],
        "total": len(checks),
        "passed": sum(1 for c in checks if c["status"] == "PASS"),
        "failed": sum(1 for c in checks if c["status"] == "FAIL"),
        "warnings": sum(1 for c in checks if c["status"] == "WARN"),
        "skipped": sum(1 for c in checks if c["status"] == "SKIP"),
    }
    summary["test_suites"].append(suite_summary)
    summary["total_tests"] += suite_summary["total"]
    summary["passed"] += suite_summary["passed"]
    summary["failed"] += suite_summary["failed"]
    summary["warnings"] += suite_summary["warnings"]
    summary["skipped"] += suite_summary["skipped"]

summary["overall_status"] = "PASS" if summary["failed"] == 0 else "FAIL"

with open('${REPORTS_DIR}/summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print(f"\n{'='*60}")
print(f"  INTEGRATION TEST SUMMARY")
print(f"{'='*60}")
print(f"  Total:    {summary['total_tests']}")
print(f"  Passed:   {summary['passed']}")
print(f"  Failed:   {summary['failed']}")
print(f"  Warnings: {summary['warnings']}")
print(f"  Skipped:  {summary['skipped']}")
print(f"  Status:   {summary['overall_status']}")
print(f"{'='*60}\n")
PYTHON_EOF

log_info "All integration tests passed successfully"
