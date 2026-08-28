"""
Project ATLAS — Shared DAG Configuration
=========================================
Centralised default_args, SLA settings, alert callbacks, and environment
detection used by all orchestration DAGs in the banking data platform
migration from Oracle DWH to AWS Lakehouse.

Technology: Apache Airflow 2.9 on Amazon MWAA
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

from airflow.models import Variable
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def get_environment() -> str:
    """Detect the current deployment environment from Airflow Variables or
    MWAA environment tags.  Falls back to 'dev'."""
    return Variable.get("atlas_environment", default_var=os.getenv("ATLAS_ENV", "dev"))


ENVIRONMENT = get_environment()

# ---------------------------------------------------------------------------
# Environment-specific settings
# ---------------------------------------------------------------------------

ENV_CONFIG: dict[str, dict[str, Any]] = {
    "dev": {
        "emr_application_id": Variable.get("atlas_emr_app_id_dev", default_var="00000000000000"),
        "emr_execution_role_arn": Variable.get("atlas_emr_role_dev", default_var="arn:aws:iam::111111111111:role/atlas-emr-dev"),
        "s3_bucket": "atlas-lakehouse-dev",
        "s3_prefix": "data",
        "dbt_target": "dev",
        "slack_conn_id": "slack_atlas_dev",
        "ge_checkpoint_store": "s3://atlas-lakehouse-dev/great_expectations/checkpoints",
        "oracle_conn_id": "oracle_dwh_dev",
        "iceberg_catalog": "atlas_iceberg_dev",
        "alert_channel": "#atlas-alerts-dev",
    },
    "staging": {
        "emr_application_id": Variable.get("atlas_emr_app_id_staging", default_var="00000000000001"),
        "emr_execution_role_arn": Variable.get("atlas_emr_role_staging", default_var="arn:aws:iam::222222222222:role/atlas-emr-staging"),
        "s3_bucket": "atlas-lakehouse-staging",
        "s3_prefix": "data",
        "dbt_target": "staging",
        "slack_conn_id": "slack_atlas_staging",
        "ge_checkpoint_store": "s3://atlas-lakehouse-staging/great_expectations/checkpoints",
        "oracle_conn_id": "oracle_dwh_staging",
        "iceberg_catalog": "atlas_iceberg_staging",
        "alert_channel": "#atlas-alerts-staging",
    },
    "prod": {
        "emr_application_id": Variable.get("atlas_emr_app_id_prod", default_var="00000000000002"),
        "emr_execution_role_arn": Variable.get("atlas_emr_role_prod", default_var="arn:aws:iam::333333333333:role/atlas-emr-prod"),
        "s3_bucket": "atlas-lakehouse-prod",
        "s3_prefix": "data",
        "dbt_target": "prod",
        "slack_conn_id": "slack_atlas_prod",
        "ge_checkpoint_store": "s3://atlas-lakehouse-prod/great_expectations/checkpoints",
        "oracle_conn_id": "oracle_dwh_prod",
        "iceberg_catalog": "atlas_iceberg_prod",
        "alert_channel": "#atlas-alerts-prod",
    },
}


def env_config() -> dict[str, Any]:
    """Return config dict for the active environment."""
    return ENV_CONFIG.get(ENVIRONMENT, ENV_CONFIG["dev"])


# ---------------------------------------------------------------------------
# SLA settings
# ---------------------------------------------------------------------------

SLA_SETTINGS = {
    "daily_ingestion": timedelta(hours=2),    # Must complete within 2h of start (02:00 -> 04:00)
    "daily_dbt": timedelta(hours=4),          # Must complete by 06:00 UTC
    "data_quality": timedelta(hours=1),       # Quality checks within 1h
    "reconciliation": timedelta(hours=2),     # Reconciliation within 2h
    "maintenance_compaction": timedelta(hours=4),  # Maintenance within 4h window
}

# ---------------------------------------------------------------------------
# Default DAG arguments
# ---------------------------------------------------------------------------

DEFAULT_ARGS: dict[str, Any] = {
    "owner": "atlas-data-engineering",
    "depends_on_past": False,
    "email": [Variable.get("atlas_alert_email", default_var="atlas-team@example.com")],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(hours=3),
    "sla": SLA_SETTINGS["daily_ingestion"],
}


def get_default_args(**overrides: Any) -> dict[str, Any]:
    """Return default_args with optional overrides."""
    args = DEFAULT_ARGS.copy()
    args.update(overrides)
    return args


# ---------------------------------------------------------------------------
# Alert / callback functions
# ---------------------------------------------------------------------------

def _build_slack_message(context: dict, level: str = "danger") -> dict:
    """Build a structured Slack message payload from task context."""
    task_instance = context.get("task_instance")
    dag_id = task_instance.dag_id if task_instance else "unknown"
    task_id = task_instance.task_id if task_instance else "unknown"
    execution_date = context.get("execution_date", "unknown")
    log_url = task_instance.log_url if task_instance else ""
    exception = context.get("exception", "")

    return {
        "attachments": [
            {
                "color": level,
                "title": f"ATLAS Pipeline Alert — {dag_id}",
                "fields": [
                    {"title": "Environment", "value": ENVIRONMENT.upper(), "short": True},
                    {"title": "DAG", "value": dag_id, "short": True},
                    {"title": "Task", "value": task_id, "short": True},
                    {"title": "Execution Date", "value": str(execution_date), "short": True},
                    {"title": "Error", "value": str(exception)[:300] if exception else "N/A", "short": False},
                ],
                "actions": [
                    {
                        "type": "button",
                        "text": "View Logs",
                        "url": log_url,
                    }
                ],
                "footer": "Project ATLAS Orchestration",
                "ts": int(datetime.utcnow().timestamp()),
            }
        ]
    }


def on_failure_callback(context: dict) -> None:
    """Send Slack alert on task failure."""
    cfg = env_config()
    try:
        hook = SlackWebhookHook(slack_webhook_conn_id=cfg["slack_conn_id"])
        message = _build_slack_message(context, level="danger")
        hook.send_dict(message)
    except Exception as e:
        # Don't let alert failures mask the real error
        print(f"[ATLAS] Failed to send Slack alert: {e}")


def on_sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis) -> None:
    """Send Slack alert when SLA is breached."""
    cfg = env_config()
    dag_id = dag.dag_id if dag else "unknown"
    missed_tasks = ", ".join(str(t) for t in task_list) if task_list else "unknown"

    message = {
        "attachments": [
            {
                "color": "warning",
                "title": f"SLA MISS — {dag_id}",
                "text": (
                    f"*Environment:* {ENVIRONMENT.upper()}\n"
                    f"*Tasks:* {missed_tasks}\n"
                    f"*Blocking:* {', '.join(str(t) for t in blocking_task_list) if blocking_task_list else 'None'}"
                ),
                "footer": "Project ATLAS SLA Monitor",
                "ts": int(datetime.utcnow().timestamp()),
            }
        ]
    }

    try:
        hook = SlackWebhookHook(slack_webhook_conn_id=cfg["slack_conn_id"])
        hook.send_dict(message)
    except Exception as e:
        print(f"[ATLAS] Failed to send SLA miss alert: {e}")


def on_retry_callback(context: dict) -> None:
    """Log retries for observability (could also push to CloudWatch metrics)."""
    task_instance = context.get("task_instance")
    print(
        f"[ATLAS] Retry {task_instance.try_number} for "
        f"{task_instance.dag_id}.{task_instance.task_id}"
    )


# ---------------------------------------------------------------------------
# Domain configuration for ingestion
# ---------------------------------------------------------------------------

INGESTION_DOMAINS = [
    {
        "name": "customer_accounts",
        "source_schema": "CORE_BANKING",
        "source_tables": [
            "CUSTOMERS", "ACCOUNTS", "ACCOUNT_TYPES",
            "CUSTOMER_ADDRESSES", "CUSTOMER_CONTACTS",
        ],
        "cdc_mode": "timestamp",
        "cdc_column": "LAST_MODIFIED_TS",
        "partition_key": "account_open_date",
        "target_database": "atlas_raw",
        "target_schema": "customer_accounts",
    },
    {
        "name": "transactions",
        "source_schema": "TRANSACTION_HISTORY",
        "source_tables": [
            "TRANSACTIONS", "TRANSACTION_TYPES", "TRANSACTION_CHANNELS",
            "PENDING_TRANSACTIONS", "SETTLEMENT_RECORDS",
        ],
        "cdc_mode": "log",
        "cdc_column": "TXN_TIMESTAMP",
        "partition_key": "transaction_date",
        "target_database": "atlas_raw",
        "target_schema": "transactions",
    },
    {
        "name": "risk_scores",
        "source_schema": "RISK_ENGINE",
        "source_tables": [
            "CREDIT_SCORES", "RISK_ASSESSMENTS", "FRAUD_FLAGS",
            "AML_ALERTS", "RISK_MODELS",
        ],
        "cdc_mode": "timestamp",
        "cdc_column": "SCORE_UPDATED_AT",
        "partition_key": "score_date",
        "target_database": "atlas_raw",
        "target_schema": "risk_scores",
    },
]

# ---------------------------------------------------------------------------
# Reconciliation tolerances
# ---------------------------------------------------------------------------

RECONCILIATION_TOLERANCES = {
    "row_count_pct": 0.001,         # 0.1% tolerance on row counts
    "aggregate_amount_pct": 0.0001, # 0.01% tolerance on financial amounts
    "field_level_mismatch_pct": 0.005,  # 0.5% field-level mismatch threshold
}

REGULATORY_TABLES = [
    "atlas_marts.regulatory.daily_transaction_report",
    "atlas_marts.regulatory.aml_suspicious_activity",
    "atlas_marts.regulatory.capital_adequacy_summary",
    "atlas_marts.regulatory.large_exposure_report",
]
