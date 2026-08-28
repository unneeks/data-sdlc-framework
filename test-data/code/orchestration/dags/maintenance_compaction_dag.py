"""
Project ATLAS — Weekly Iceberg Table Maintenance DAG
=====================================================
Performs Apache Iceberg table maintenance operations to ensure optimal
query performance and storage efficiency:

  1. Snapshot expiry — remove snapshots older than retention period
  2. Orphan file removal — clean up unreferenced data files
  3. Compaction — rewrite small files into optimally-sized ones

Technology: SparkSQL on EMR Serverless
Schedule:   Weekly on Sundays at 22:00 UTC
SLA:        Must complete within 4-hour maintenance window
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.emr import EmrServerlessStartJobRunOperator
from airflow.providers.amazon.aws.sensors.emr import EmrServerlessJobSensor
from airflow.utils.task_group import TaskGroup

from config.dag_config import (
    INGESTION_DOMAINS,
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
DAG_ID = "atlas_maintenance_compaction"
SCHEDULE = "0 22 * * 0"  # Sundays at 22:00 UTC
START_DATE = datetime(2025, 1, 1)

# Iceberg tables to maintain (all layers)
ICEBERG_TABLES = []
for domain in INGESTION_DOMAINS:
    # Raw layer tables
    for table in domain["source_tables"]:
        ICEBERG_TABLES.append(
            f"{domain['target_database']}.{domain['target_schema']}.{table.lower()}"
        )

# Marts layer tables
MARTS_TABLES = [
    "atlas_marts.customer_360.customer_summary",
    "atlas_marts.customer_360.account_health",
    "atlas_marts.transactions.daily_transaction_summary",
    "atlas_marts.transactions.merchant_analytics",
    "atlas_marts.risk.risk_score_history",
    "atlas_marts.risk.fraud_detection_metrics",
    "atlas_marts.regulatory.daily_transaction_report",
    "atlas_marts.regulatory.aml_suspicious_activity",
    "atlas_marts.regulatory.capital_adequacy_summary",
]
ICEBERG_TABLES.extend(MARTS_TABLES)

# Maintenance configuration
SNAPSHOT_RETENTION_DAYS = 7
ORPHAN_FILE_RETENTION_MS = 7 * 24 * 60 * 60 * 1000  # 7 days in milliseconds
COMPACTION_TARGET_FILE_SIZE_BYTES = 256 * 1024 * 1024  # 256 MB

SPARK_MAINTENANCE_DRIVER = {
    "sparkSubmit": {
        "entryPoint": f"s3://{CFG['s3_bucket']}/spark-jobs/maintenance/iceberg_maintenance.py",
        "entryPointArguments": [],
        "sparkSubmitParameters": (
            "--conf spark.executor.cores=4 "
            "--conf spark.executor.memory=16g "
            "--conf spark.driver.cores=4 "
            "--conf spark.driver.memory=8g "
            "--conf spark.dynamicAllocation.enabled=true "
            "--conf spark.dynamicAllocation.minExecutors=1 "
            "--conf spark.dynamicAllocation.maxExecutors=10 "
            "--conf spark.sql.catalog.atlas_iceberg=org.apache.iceberg.spark.SparkCatalog "
            "--conf spark.sql.catalog.atlas_iceberg.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog "
            "--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions "
            "--conf spark.hadoop.hive.metastore.client.factory.class="
            "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
        ),
    }
}

CONFIGURATION_OVERRIDES = {
    "monitoringConfiguration": {
        "s3MonitoringConfiguration": {
            "logUri": f"s3://{CFG['s3_bucket']}/emr-logs/maintenance/"
        }
    }
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _build_maintenance_sql(table: str, operation: str) -> str:
    """Generate Iceberg maintenance SQL for a given operation."""
    catalog_table = f"atlas_iceberg.{table}"

    if operation == "expire_snapshots":
        retention_ts = (
            datetime.utcnow() - timedelta(days=SNAPSHOT_RETENTION_DAYS)
        ).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"CALL atlas_iceberg.system.expire_snapshots("
            f"table => '{table}', "
            f"older_than => TIMESTAMP '{retention_ts}', "
            f"retain_last => 3"
            f")"
        )
    elif operation == "remove_orphan_files":
        retention_ts = (
            datetime.utcnow() - timedelta(days=SNAPSHOT_RETENTION_DAYS)
        ).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"CALL atlas_iceberg.system.remove_orphan_files("
            f"table => '{table}', "
            f"older_than => TIMESTAMP '{retention_ts}'"
            f")"
        )
    elif operation == "compaction":
        return (
            f"CALL atlas_iceberg.system.rewrite_data_files("
            f"table => '{table}', "
            f"options => map("
            f"'target-file-size-bytes', '{COMPACTION_TARGET_FILE_SIZE_BYTES}', "
            f"'min-file-size-bytes', '{COMPACTION_TARGET_FILE_SIZE_BYTES // 4}', "
            f"'max-file-size-bytes', '{COMPACTION_TARGET_FILE_SIZE_BYTES * 2}'"
            f")"
            f")"
        )
    else:
        raise ValueError(f"Unknown maintenance operation: {operation}")


def _build_maintenance_job_driver(tables: list[str], operation: str) -> dict:
    """Build EMR Serverless job driver for a batch of maintenance operations."""
    driver = json.loads(json.dumps(SPARK_MAINTENANCE_DRIVER))
    driver["sparkSubmit"]["entryPointArguments"] = [
        "--operation", operation,
        "--tables", ",".join(tables),
        "--snapshot-retention-days", str(SNAPSHOT_RETENTION_DAYS),
        "--target-file-size", str(COMPACTION_TARGET_FILE_SIZE_BYTES),
        "--catalog", CFG["iceberg_catalog"],
    ]
    return driver


def pre_maintenance_check(**context) -> None:
    """Check there are no active writes before starting maintenance."""
    import boto3

    emr_client = boto3.client("emr-serverless")

    # Check for running ingestion jobs
    response = emr_client.list_job_runs(
        applicationId=CFG["emr_application_id"],
        states=["RUNNING", "SUBMITTED", "PENDING"],
    )

    active_jobs = [
        j for j in response.get("jobRuns", [])
        if "ingest" in j.get("name", "").lower()
    ]

    if active_jobs:
        raise RuntimeError(
            f"[ATLAS] Cannot start maintenance — {len(active_jobs)} ingestion "
            f"job(s) still running: {[j['name'] for j in active_jobs]}"
        )

    print("[ATLAS] No active ingestion jobs. Safe to proceed with maintenance.")


def post_maintenance_report(**context) -> None:
    """Generate maintenance summary report."""
    ti = context["ti"]
    print(
        f"[ATLAS] Maintenance complete for {len(ICEBERG_TABLES)} tables. "
        f"Operations: expire_snapshots, remove_orphan_files, compaction."
    )


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

with DAG(
    dag_id=DAG_ID,
    default_args=get_default_args(
        retries=1,
        retry_delay=timedelta(minutes=10),
        on_failure_callback=on_failure_callback,
        on_retry_callback=on_retry_callback,
        sla=SLA_SETTINGS["maintenance_compaction"],
        execution_timeout=timedelta(hours=4),
    ),
    description="Weekly Iceberg table maintenance: snapshot expiry, orphan removal, compaction",
    schedule=SCHEDULE,
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    tags=["atlas", "maintenance", "iceberg", "compaction", "weekly"],
    doc_md=__doc__,
    sla_miss_callback=on_sla_miss_callback,
) as dag:

    start = EmptyOperator(task_id="start")

    pre_check = PythonOperator(
        task_id="pre_maintenance_check",
        python_callable=pre_maintenance_check,
        execution_timeout=timedelta(minutes=5),
    )

    # -----------------------------------------------------------------------
    # Maintenance operations (sequential: expire -> orphan -> compact)
    # -----------------------------------------------------------------------

    # Stage 1: Expire old snapshots
    with TaskGroup(group_id="expire_snapshots") as expire_group:
        submit_expire = EmrServerlessStartJobRunOperator(
            task_id="submit_expire_snapshots",
            application_id=CFG["emr_application_id"],
            execution_role_arn=CFG["emr_execution_role_arn"],
            job_driver=_build_maintenance_job_driver(ICEBERG_TABLES, "expire_snapshots"),
            configuration_overrides=CONFIGURATION_OVERRIDES,
            name="atlas-maintenance-expire-snapshots-{{ ds }}",
            wait_for_completion=False,
            aws_conn_id="aws_default",
        )

        wait_expire = EmrServerlessJobSensor(
            task_id="wait_expire_snapshots",
            application_id=CFG["emr_application_id"],
            job_run_id=submit_expire.output,
            aws_conn_id="aws_default",
            poke_interval=120,
            timeout=3600,
        )

        submit_expire >> wait_expire

    # Stage 2: Remove orphan files (must run after snapshot expiry)
    with TaskGroup(group_id="remove_orphan_files") as orphan_group:
        submit_orphan = EmrServerlessStartJobRunOperator(
            task_id="submit_orphan_removal",
            application_id=CFG["emr_application_id"],
            execution_role_arn=CFG["emr_execution_role_arn"],
            job_driver=_build_maintenance_job_driver(ICEBERG_TABLES, "remove_orphan_files"),
            configuration_overrides=CONFIGURATION_OVERRIDES,
            name="atlas-maintenance-orphan-removal-{{ ds }}",
            wait_for_completion=False,
            aws_conn_id="aws_default",
        )

        wait_orphan = EmrServerlessJobSensor(
            task_id="wait_orphan_removal",
            application_id=CFG["emr_application_id"],
            job_run_id=submit_orphan.output,
            aws_conn_id="aws_default",
            poke_interval=120,
            timeout=3600,
        )

        submit_orphan >> wait_orphan

    # Stage 3: Compaction (rewrite small files)
    with TaskGroup(group_id="compaction") as compaction_group:
        submit_compact = EmrServerlessStartJobRunOperator(
            task_id="submit_compaction",
            application_id=CFG["emr_application_id"],
            execution_role_arn=CFG["emr_execution_role_arn"],
            job_driver=_build_maintenance_job_driver(ICEBERG_TABLES, "compaction"),
            configuration_overrides=CONFIGURATION_OVERRIDES,
            name="atlas-maintenance-compaction-{{ ds }}",
            wait_for_completion=False,
            aws_conn_id="aws_default",
        )

        wait_compact = EmrServerlessJobSensor(
            task_id="wait_compaction",
            application_id=CFG["emr_application_id"],
            job_run_id=submit_compact.output,
            aws_conn_id="aws_default",
            poke_interval=120,
            timeout=7200,  # Compaction can take longer
        )

        submit_compact >> wait_compact

    # -----------------------------------------------------------------------
    # Post-maintenance report
    # -----------------------------------------------------------------------

    report = PythonOperator(
        task_id="post_maintenance_report",
        python_callable=post_maintenance_report,
        trigger_rule="all_success",
    )

    end = EmptyOperator(task_id="end")

    # -----------------------------------------------------------------------
    # Task dependencies — operations must be sequential
    # -----------------------------------------------------------------------

    (
        start
        >> pre_check
        >> expire_group
        >> orphan_group
        >> compaction_group
        >> report
        >> end
    )
