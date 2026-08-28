"""
Project ATLAS — Daily CDC Ingestion DAG
=========================================
Orchestrates Apache Spark CDC ingestion jobs for all banking domains:
  - customer_accounts
  - transactions
  - risk_scores

Technology: EMR Serverless via EmrServerlessStartJobRunOperator
Schedule:   Daily at 02:00 UTC
SLA:        Must complete by 04:00 UTC (2-hour window)

The DAG dynamically generates task groups per domain, with each domain
running independently so a failure in one domain does not block others.
A final sensor confirms all domains have landed before marking success.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
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
DAG_ID = "atlas_daily_ingestion"
SCHEDULE = "0 2 * * *"  # Daily at 02:00 UTC
START_DATE = datetime(2025, 1, 1)

SPARK_JOB_DRIVER_TEMPLATE = {
    "sparkSubmit": {
        "entryPoint": "s3://{bucket}/spark-jobs/cdc_ingestion/main.py",
        "entryPointArguments": [],
        "sparkSubmitParameters": (
            "--conf spark.executor.cores=4 "
            "--conf spark.executor.memory=16g "
            "--conf spark.driver.cores=4 "
            "--conf spark.driver.memory=8g "
            "--conf spark.dynamicAllocation.enabled=true "
            "--conf spark.dynamicAllocation.minExecutors=2 "
            "--conf spark.dynamicAllocation.maxExecutors=20 "
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
            "logUri": f"s3://{CFG['s3_bucket']}/emr-logs/ingestion/"
        }
    }
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _build_job_driver(domain: dict, execution_date: str) -> dict:
    """Build the Spark job driver config for a given domain."""
    driver = json.loads(
        json.dumps(SPARK_JOB_DRIVER_TEMPLATE).replace("{bucket}", CFG["s3_bucket"])
    )
    driver["sparkSubmit"]["entryPointArguments"] = [
        "--domain", domain["name"],
        "--source-schema", domain["source_schema"],
        "--source-tables", ",".join(domain["source_tables"]),
        "--cdc-mode", domain["cdc_mode"],
        "--cdc-column", domain["cdc_column"],
        "--partition-key", domain["partition_key"],
        "--target-database", domain["target_database"],
        "--target-schema", domain["target_schema"],
        "--execution-date", execution_date,
        "--catalog", CFG["iceberg_catalog"],
    ]
    return driver


def pre_ingestion_check(**context) -> None:
    """Validate prerequisites before launching ingestion jobs."""
    import boto3

    execution_date = context["ds"]
    print(f"[ATLAS] Pre-ingestion checks for execution_date={execution_date}")

    # Verify EMR Serverless application is in STARTED state
    client = boto3.client("emr-serverless")
    response = client.get_application(applicationId=CFG["emr_application_id"])
    state = response["application"]["state"]

    if state != "STARTED":
        raise RuntimeError(
            f"EMR Serverless application {CFG['emr_application_id']} "
            f"is in state '{state}', expected 'STARTED'"
        )

    print(f"[ATLAS] EMR application is STARTED. Proceeding with ingestion.")


def post_ingestion_validation(**context) -> None:
    """Run lightweight post-ingestion checks (file counts, partition presence)."""
    import boto3

    execution_date = context["ds"]
    s3 = boto3.client("s3")

    for domain in INGESTION_DOMAINS:
        prefix = (
            f"{CFG['s3_prefix']}/{domain['target_database']}/"
            f"{domain['target_schema']}/{domain['partition_key']}={execution_date}/"
        )
        response = s3.list_objects_v2(
            Bucket=CFG["s3_bucket"],
            Prefix=prefix,
            MaxKeys=1,
        )
        if response.get("KeyCount", 0) == 0:
            raise RuntimeError(
                f"[ATLAS] No data files found for domain '{domain['name']}' "
                f"at s3://{CFG['s3_bucket']}/{prefix}"
            )

    print(f"[ATLAS] Post-ingestion validation passed for all domains.")


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

with DAG(
    dag_id=DAG_ID,
    default_args=get_default_args(
        retries=3,
        retry_delay=timedelta(minutes=5),
        on_failure_callback=on_failure_callback,
        on_retry_callback=on_retry_callback,
        sla=SLA_SETTINGS["daily_ingestion"],
    ),
    description="Daily CDC ingestion from Oracle DWH to Iceberg lakehouse for all banking domains",
    schedule=SCHEDULE,
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    tags=["atlas", "ingestion", "cdc", "emr-serverless", "daily"],
    doc_md=__doc__,
    sla_miss_callback=on_sla_miss_callback,
) as dag:

    start = EmptyOperator(task_id="start")

    pre_check = PythonOperator(
        task_id="pre_ingestion_check",
        python_callable=pre_ingestion_check,
        execution_timeout=timedelta(minutes=5),
    )

    all_domain_tasks = []

    for domain in INGESTION_DOMAINS:
        domain_name = domain["name"]

        with TaskGroup(group_id=f"ingest_{domain_name}") as tg:
            submit_job = EmrServerlessStartJobRunOperator(
                task_id=f"submit_{domain_name}",
                application_id=CFG["emr_application_id"],
                execution_role_arn=CFG["emr_execution_role_arn"],
                job_driver=_build_job_driver(domain, "{{ ds }}"),
                configuration_overrides=CONFIGURATION_OVERRIDES,
                name=f"atlas-ingest-{domain_name}-{{{{ ds }}}}",
                wait_for_completion=False,
                aws_conn_id="aws_default",
            )

            wait_for_job = EmrServerlessJobSensor(
                task_id=f"wait_{domain_name}",
                application_id=CFG["emr_application_id"],
                job_run_id=submit_job.output,
                aws_conn_id="aws_default",
                poke_interval=60,
                timeout=7200,  # 2 hours max wait
            )

            submit_job >> wait_for_job

        all_domain_tasks.append(tg)

    post_validation = PythonOperator(
        task_id="post_ingestion_validation",
        python_callable=post_ingestion_validation,
        execution_timeout=timedelta(minutes=10),
        trigger_rule="all_success",
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule="all_success",
    )

    # Task dependencies
    start >> pre_check >> all_domain_tasks >> post_validation >> end
