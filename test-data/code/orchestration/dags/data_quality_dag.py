"""
Project ATLAS — Data Quality Validation DAG
=============================================
Runs Great Expectations validation suites after dbt transformations complete.

Checks performed:
  - Row count expectations (vs historical baselines)
  - Null rate thresholds on critical columns
  - Distribution checks (statistical boundaries)
  - Cross-system reconciliation vs Oracle DWH outputs

On failure: quarantine affected partitions and alert via Slack.

Technology: Great Expectations with Spark/Athena backend
Schedule:   Daily (triggered after dbt DAG completes)
SLA:        Must complete within 1 hour of starting
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.task_group import TaskGroup

from config.dag_config import (
    INGESTION_DOMAINS,
    SLA_SETTINGS,
    env_config,
    get_default_args,
    on_failure_callback,
    on_sla_miss_callback,
)

# ---------------------------------------------------------------------------
# DAG-level configuration
# ---------------------------------------------------------------------------

CFG = env_config()
DAG_ID = "atlas_data_quality"
SCHEDULE = "0 2 * * *"  # Same schedule; sensor gates on dbt completion
START_DATE = datetime(2025, 1, 1)

GE_PROJECT_DIR = "/usr/local/airflow/great_expectations"
QUARANTINE_BUCKET = CFG["s3_bucket"]
QUARANTINE_PREFIX = "quarantine"


# ---------------------------------------------------------------------------
# Validation suite definitions
# ---------------------------------------------------------------------------

VALIDATION_SUITES = [
    {
        "name": "row_count_validation",
        "checkpoint": "atlas_row_counts",
        "description": "Verify row counts are within expected range based on historical patterns",
        "severity": "critical",
    },
    {
        "name": "null_rate_validation",
        "checkpoint": "atlas_null_rates",
        "description": "Check null rates on critical columns do not exceed thresholds",
        "severity": "critical",
    },
    {
        "name": "distribution_validation",
        "checkpoint": "atlas_distributions",
        "description": "Statistical distribution checks on numeric columns",
        "severity": "warning",
    },
    {
        "name": "reconciliation_validation",
        "checkpoint": "atlas_oracle_reconciliation",
        "description": "Cross-system reconciliation vs Oracle DWH outputs",
        "severity": "critical",
    },
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def run_ge_checkpoint(checkpoint_name: str, execution_date: str, **context) -> dict:
    """Run a Great Expectations checkpoint and return results."""
    import great_expectations as gx
    from great_expectations.checkpoint import Checkpoint

    ge_context = gx.get_context(context_root_dir=GE_PROJECT_DIR)

    result = ge_context.run_checkpoint(
        checkpoint_name=checkpoint_name,
        run_name=f"atlas_{checkpoint_name}_{execution_date}",
        batch_request={
            "runtime_parameters": {
                "execution_date": execution_date,
            }
        },
    )

    # Push results to XCom
    success = result.success
    statistics = result.statistics
    context["ti"].xcom_push(
        key=f"{checkpoint_name}_success", value=success
    )
    context["ti"].xcom_push(
        key=f"{checkpoint_name}_stats",
        value={
            "evaluated_expectations": statistics.get("evaluated_expectations", 0),
            "successful_expectations": statistics.get("successful_expectations", 0),
            "unsuccessful_expectations": statistics.get("unsuccessful_expectations", 0),
            "success_percent": statistics.get("success_percent", 0),
        },
    )

    if not success:
        raise ValueError(
            f"[ATLAS] Great Expectations checkpoint '{checkpoint_name}' FAILED. "
            f"Pass rate: {statistics.get('success_percent', 0):.1f}%"
        )

    return {"success": success, "statistics": statistics}


def quarantine_failed_data(**context) -> None:
    """Move failed partitions to quarantine location in S3."""
    import boto3

    execution_date = context["ds"]
    ti = context["ti"]
    s3 = boto3.client("s3")

    quarantined_domains = []

    for suite in VALIDATION_SUITES:
        if suite["severity"] != "critical":
            continue

        checkpoint_success = ti.xcom_pull(
            key=f"{suite['checkpoint']}_success",
            task_ids=f"validation_suites.run_{suite['name']}",
        )

        if checkpoint_success is False:
            # Tag the partition as quarantined rather than moving data
            for domain in INGESTION_DOMAINS:
                quarantine_marker = (
                    f"{QUARANTINE_PREFIX}/{domain['name']}/"
                    f"execution_date={execution_date}/"
                    f"_QUARANTINED_{suite['name']}"
                )
                s3.put_object(
                    Bucket=QUARANTINE_BUCKET,
                    Key=quarantine_marker,
                    Body=f"Quarantined due to failed {suite['name']} at {datetime.utcnow().isoformat()}",
                )
                quarantined_domains.append(domain["name"])

    if quarantined_domains:
        context["ti"].xcom_push(
            key="quarantined_domains",
            value=list(set(quarantined_domains)),
        )
        print(
            f"[ATLAS] Quarantined data for domains: {quarantined_domains} "
            f"on execution_date={execution_date}"
        )


def build_quality_report(**context) -> str:
    """Build a summary report of all validation results."""
    ti = context["ti"]
    execution_date = context["ds"]
    report_lines = [
        f"*ATLAS Data Quality Report — {execution_date}*\n",
        "| Suite | Status | Pass Rate |",
        "|-------|--------|-----------|",
    ]

    all_passed = True
    for suite in VALIDATION_SUITES:
        stats = ti.xcom_pull(
            key=f"{suite['checkpoint']}_stats",
            task_ids=f"validation_suites.run_{suite['name']}",
        )
        success = ti.xcom_pull(
            key=f"{suite['checkpoint']}_success",
            task_ids=f"validation_suites.run_{suite['name']}",
        )

        status_emoji = "PASS" if success else "FAIL"
        pass_rate = stats.get("success_percent", 0) if stats else "N/A"

        if not success:
            all_passed = False

        report_lines.append(
            f"| {suite['name']} | {status_emoji} | {pass_rate}% |"
        )

    quarantined = ti.xcom_pull(key="quarantined_domains", task_ids="quarantine_failed_data")
    if quarantined:
        report_lines.append(f"\n*Quarantined domains:* {', '.join(quarantined)}")

    report = "\n".join(report_lines)
    ti.xcom_push(key="quality_report", value=report)
    return report


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

with DAG(
    dag_id=DAG_ID,
    default_args=get_default_args(
        retries=1,
        retry_delay=timedelta(minutes=2),
        on_failure_callback=on_failure_callback,
        sla=SLA_SETTINGS["data_quality"],
    ),
    description="Data quality validation using Great Expectations after dbt transformations",
    schedule=SCHEDULE,
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    tags=["atlas", "data-quality", "great-expectations", "daily"],
    doc_md=__doc__,
    sla_miss_callback=on_sla_miss_callback,
) as dag:

    start = EmptyOperator(task_id="start")

    # -----------------------------------------------------------------------
    # Wait for dbt DAG to complete
    # -----------------------------------------------------------------------

    wait_for_dbt = ExternalTaskSensor(
        task_id="wait_for_dbt",
        external_dag_id="atlas_daily_dbt",
        external_task_id="end",
        allowed_states=["success"],
        failed_states=["failed", "skipped"],
        mode="reschedule",
        poke_interval=120,
        timeout=7200,
        execution_timeout=timedelta(hours=2, minutes=30),
    )

    # -----------------------------------------------------------------------
    # Validation suites (run in parallel within a TaskGroup)
    # -----------------------------------------------------------------------

    with TaskGroup(group_id="validation_suites") as validation_group:
        for suite in VALIDATION_SUITES:
            PythonOperator(
                task_id=f"run_{suite['name']}",
                python_callable=run_ge_checkpoint,
                op_kwargs={
                    "checkpoint_name": suite["checkpoint"],
                    "execution_date": "{{ ds }}",
                },
                execution_timeout=timedelta(minutes=30),
                # Don't fail the whole DAG on a single suite failure
                # — we want to run quarantine logic regardless
                trigger_rule="all_done",
            )

    # -----------------------------------------------------------------------
    # Quarantine failed data
    # -----------------------------------------------------------------------

    quarantine = PythonOperator(
        task_id="quarantine_failed_data",
        python_callable=quarantine_failed_data,
        trigger_rule="all_done",
        execution_timeout=timedelta(minutes=10),
    )

    # -----------------------------------------------------------------------
    # Build quality report
    # -----------------------------------------------------------------------

    report = PythonOperator(
        task_id="build_quality_report",
        python_callable=build_quality_report,
        trigger_rule="all_done",
    )

    # -----------------------------------------------------------------------
    # Slack alert on failure
    # -----------------------------------------------------------------------

    slack_alert = SlackWebhookOperator(
        task_id="slack_quality_alert",
        slack_webhook_conn_id=CFG["slack_conn_id"],
        message="{{ ti.xcom_pull(key='quality_report', task_ids='build_quality_report') }}",
        channel=CFG["alert_channel"],
        trigger_rule="all_done",
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule="none_failed_min_one_success",
    )

    # -----------------------------------------------------------------------
    # Task dependencies
    # -----------------------------------------------------------------------

    (
        start
        >> wait_for_dbt
        >> validation_group
        >> quarantine
        >> report
        >> slack_alert
        >> end
    )
