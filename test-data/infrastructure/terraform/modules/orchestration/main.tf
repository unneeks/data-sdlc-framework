##############################################################################
# Project ATLAS — Orchestration Module
# Amazon MWAA (Managed Workflows for Apache Airflow)
#
# Orchestrates:
# - Nightly batch CDC ingestion pipelines
# - Bronze → Silver → Gold transformation DAGs
# - Data quality validation checks
# - SLA monitoring and alerting
# - Reconciliation jobs (Oracle vs Lakehouse)
##############################################################################

# ===========================================================================
# MWAA Environment
# ===========================================================================

resource "aws_mwaa_environment" "atlas" {
  name               = "${var.name_prefix}-airflow"
  airflow_version    = "2.8.1"
  environment_class  = var.mwaa_environment_class
  max_workers        = var.mwaa_max_workers
  min_workers        = 1

  execution_role_arn = aws_iam_role.mwaa_execution.arn
  kms_key           = var.kms_key_arn

  source_bucket_arn    = var.dags_bucket_arn
  dag_s3_path          = "dags/"
  requirements_s3_path = "requirements/requirements.txt"
  plugins_s3_path      = "plugins/plugins.zip"

  webserver_access_mode = "PRIVATE_ONLY"

  network_configuration {
    security_group_ids = [var.security_group_id]
    subnet_ids         = slice(var.private_subnet_ids, 0, 2) # MWAA requires exactly 2 subnets
  }

  logging_configuration {
    dag_processing_logs {
      enabled   = true
      log_level = "INFO"
    }
    scheduler_logs {
      enabled   = true
      log_level = "WARNING"
    }
    task_logs {
      enabled   = true
      log_level = "INFO"
    }
    webserver_logs {
      enabled   = true
      log_level = "WARNING"
    }
    worker_logs {
      enabled   = true
      log_level = "INFO"
    }
  }

  airflow_configuration_options = {
    "core.default_timezone"             = "Europe/London"
    "core.parallelism"                  = "32"
    "core.max_active_runs_per_dag"      = "1"
    "scheduler.catchup_by_default"      = "false"
    "webserver.default_ui_timezone"     = "Europe/London"
    "celery.worker_autoscale"           = "${var.mwaa_max_workers},1"
    "secrets.backend"                   = "airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend"
    "secrets.backend_kwargs"            = "{\"connections_prefix\": \"airflow/connections\", \"variables_prefix\": \"airflow/variables\"}"
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-airflow"
    Service = "mwaa"
  })
}

# ===========================================================================
# MWAA Execution Role
# ===========================================================================

resource "aws_iam_role" "mwaa_execution" {
  name = "${var.name_prefix}-mwaa-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "airflow.amazonaws.com",
            "airflow-env.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy" "mwaa_execution" {
  name = "${var.name_prefix}-mwaa-execution-policy"
  role = aws_iam_role.mwaa_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AirflowPublishMetrics"
        Effect = "Allow"
        Action = [
          "airflow:PublishMetrics"
        ]
        Resource = "arn:aws:airflow:${var.region}:*:environment/${var.name_prefix}-airflow"
      },
      {
        Sid    = "S3DAGsAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject*",
          "s3:GetBucket*",
          "s3:List*"
        ]
        Resource = [
          var.dags_bucket_arn,
          "${var.dags_bucket_arn}/*"
        ]
      },
      {
        Sid    = "S3DataLakeAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::meridian-atlas-*",
          "arn:aws:s3:::meridian-atlas-*/*"
        ]
      },
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:GetLogRecord",
          "logs:GetLogGroupFields",
          "logs:GetQueryResults"
        ]
        Resource = "arn:aws:logs:${var.region}:*:log-group:airflow-*"
      },
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Sid    = "EMRServerlessAccess"
        Effect = "Allow"
        Action = [
          "emr-serverless:StartJobRun",
          "emr-serverless:GetJobRun",
          "emr-serverless:CancelJobRun",
          "emr-serverless:ListJobRuns"
        ]
        Resource = "*"
      },
      {
        Sid    = "GlueAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions",
          "glue:BatchGetPartition"
        ]
        Resource = "*"
      },
      {
        Sid    = "KMSAccess"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:GenerateDataKey*",
          "kms:Encrypt"
        ]
        Resource = [var.kms_key_arn]
      },
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.region}:*:secret:airflow/*"
      },
      {
        Sid    = "SQSAccess"
        Effect = "Allow"
        Action = [
          "sqs:ChangeMessageVisibility",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ReceiveMessage",
          "sqs:SendMessage"
        ]
        Resource = "arn:aws:sqs:${var.region}:*:airflow-celery-*"
      }
    ]
  })
}
