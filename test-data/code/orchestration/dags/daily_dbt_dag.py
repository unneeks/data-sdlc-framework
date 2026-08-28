"""
Project ATLAS — Daily dbt Transformation DAG
==============================================
Runs dbt transformations after the ingestion DAG completes successfully.
Uses an ExternalTaskSensor to wait for atlas_daily_ingestion completion.

Stages:
  1. dbt deps — install dbt packages
  2. dbt run (staging models) — incremental staging layer
  3. dbt run (marts models) — business-layer aggregations
  4. dbt test — run all data tests and schema contracts

Technology: dbt-core with dbt-spark/dbt-glue adapter, executed via BashOperator
Schedule:   Triggered after ingestion (runs daily, scheduled at 02:00 UTC with sensor)
SLA:        Must complete by 06:00 UTC
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

from config.dag_config import (
    SLA_SETTINGS,
    env_config,
    get_default_args,
    on_failure_callback,
    on_retry_callback,
    on_sla_miss_callback,
)

# ---------------------------------------------------------------------------
# DAG-level configuration
# ---------------------------------------------------------------------------

CFG = env_config()
DAG_ID = "atlas_daily_dbt"
SCHEDULE = "0 2 * * *"  # Same schedule as ingestion; sensor gates execution
START_DATE = datetime(2025, 1, 1)

DBT_PROJECT_DIR = "/usr/local/airflow/dbt/atlas_lakehouse"
DBT_PROFILES_DIR = "/usr/local/airflow/dbt/profiles"
DBT_TARGET = CFG["dbt_target"]

# Base dbt command with common flags
DBT_BASE_CMD = (
    f"cd {DBT_PROJECT_DIR} && "
    f"dbt --no-use-colors "
    f"--profiles-dir {DBT_PROFILES_DIR} "
    f"--target {DBT_TARGET} "
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def log_dbt_run_results(**context) -> None:
    """Parse dbt run_results.json and log summary metrics."""
    import json
    from pathlib import Path

    results_path = Path(DBT_PROJECT_DIR) / "target" / "run_results.json"

    if not results_path.exists():
        print("[ATLAS] No run_results.json found — skipping summary.")
        return

    with open(results_path) as f:
        results = json.load(f)

    total = len(results.get("results", []))
    successes = sum(1 for r in results["results"] if r["status"] == "success")
    errors = sum(1 for r in results["results"] if r["status"] == "error")
    skipped = sum(1 for r in results["results"] if r["status"] == "skipped")
    total_time = results.get("elapsed_time", 0)

    print(
        f"[ATLAS] dbt run summary: "
        f"{successes}/{total} succeeded, {errors} errors, {skipped} skipped. "
        f"Total time: {total_time:.1f}s"
    )

    # Push metrics to XCom for downstream use
    context["ti"].xcom_push(key="dbt_total_models", value=total)
    context["ti"].xcom_push(key="dbt_errors", value=errors)
    context["ti"].xcom_push(key="dbt_elapsed_time", value=total_time)


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

with DAG(
    dag_id=DAG_ID,
    default_args=get_default_args(
        retries=2,
        retry_delay=timedelta(minutes=3),
        on_failure_callback=on_failure_callback,
        on_retry_callback=on_retry_callback,
        sla=SLA_SETTINGS["daily_dbt"],
    ),
    description="Run dbt staging and marts transformations after daily ingestion completes",
    schedule=SCHEDULE,
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    tags=["atlas", "dbt", "transformations", "daily"],
    doc_md=__doc__,
    sla_miss_callback=on_sla_miss_callback,
) as dag:

    start = EmptyOperator(task_id="start")

    # -----------------------------------------------------------------------
    # Wait for ingestion DAG to complete
    # -----------------------------------------------------------------------

    wait_for_ingestion = ExternalTaskSensor(
        task_id="wait_for_ingestion",
        external_dag_id="atlas_daily_ingestion",
        external_task_id="end",
        allowed_states=["success"],
        failed_states=["failed", "skipped"],
        mode="reschedule",
        poke_interval=120,  # Check every 2 minutes
        timeout=7200,       # Wait up to 2 hours
        execution_timeout=timedelta(hours=2, minutes=30),
    )

    # -----------------------------------------------------------------------
    # dbt deps — install packages
    # -----------------------------------------------------------------------

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{DBT_BASE_CMD} deps",
        execution_timeout=timedelta(minutes=10),
        retries=3,
        retry_delay=timedelta(minutes=1),
    )

    # -----------------------------------------------------------------------
    # dbt run — staging models (incremental)
    # -----------------------------------------------------------------------

    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=(
            f"{DBT_BASE_CMD} run "
            f"--select staging "
            f"--vars '{{\"execution_date\": \"{{{{ ds }}}}\"}}' "
            f"--full-refresh={{{{ var.value.get('atlas_dbt_full_refresh', 'false') }}}}"
        ),
        execution_timeout=timedelta(hours=1),
    )

    # -----------------------------------------------------------------------
    # dbt run — marts models
    # -----------------------------------------------------------------------

    dbt_run_marts = BashOperator(
        task_id="dbt_run_marts",
        bash_command=(
            f"{DBT_BASE_CMD} run "
            f"--select marts "
            f"--vars '{{\"execution_date\": \"{{{{ ds }}}}\"}}'"
        ),
        execution_timeout=timedelta(hours=1, minutes=30),
    )

    # -----------------------------------------------------------------------
    # dbt test — run schema tests and data tests
    # -----------------------------------------------------------------------

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"{DBT_BASE_CMD} test "
            f"--select staging marts "
            f"--vars '{{\"execution_date\": \"{{{{ ds }}}}\"}}'"
        ),
        execution_timeout=timedelta(minutes=45),
    )

    # -----------------------------------------------------------------------
    # Log results summary
    # -----------------------------------------------------------------------

    log_results = PythonOperator(
        task_id="log_dbt_results",
        python_callable=log_dbt_run_results,
        trigger_rule="all_done",  # Run even if tests fail to capture results
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule="all_success",
    )

    # -----------------------------------------------------------------------
    # Task dependencies
    # -----------------------------------------------------------------------

    (
        start
        >> wait_for_ingestion
        >> dbt_deps
        >> dbt_run_staging
        >> dbt_run_marts
        >> dbt_test
        >> log_results
        >> end
    )
