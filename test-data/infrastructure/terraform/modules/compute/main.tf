##############################################################################
# Project ATLAS — Compute Module
# EMR Serverless Application for Apache Spark batch transformations
#
# Used for:
# - Bronze → Silver data cleansing and conforming
# - Silver → Gold aggregation and business logic
# - Data quality validation jobs
# - Schema evolution handling
#
# Security:
# - Runs in private VPC subnets
# - KMS encryption for at-rest data
# - Auto-stop to control costs
# - Security configuration enforces encryption in transit
##############################################################################

# ===========================================================================
# EMR Serverless Application
# ===========================================================================

resource "aws_emrserverless_application" "spark" {
  name          = "${var.name_prefix}-spark"
  release_label = var.emr_spark_version
  type          = "spark"

  initial_capacity {
    initial_capacity_type = "Driver"

    initial_capacity_config {
      worker_count = 1
      worker_configuration {
        cpu    = "4 vCPU"
        memory = "16 GB"
      }
    }
  }

  initial_capacity {
    initial_capacity_type = "Executor"

    initial_capacity_config {
      worker_count = 2
      worker_configuration {
        cpu    = var.emr_worker_cpu
        memory = var.emr_worker_memory
      }
    }
  }

  maximum_capacity {
    cpu    = "${var.emr_max_workers * 4} vCPU"
    memory = "${var.emr_max_workers * 16} GB"
    disk   = "${var.emr_max_workers * 200} GB"
  }

  auto_start_configuration {
    enabled = true
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }

  network_configuration {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.security_group_id]
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-spark"
    Service = "emr-serverless"
  })
}

# ===========================================================================
# IAM Role for EMR Serverless Job Execution
# ===========================================================================

resource "aws_iam_role" "emr_execution" {
  name = "${var.name_prefix}-emr-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "emr-serverless.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = var.common_tags
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy" "emr_execution" {
  name = "${var.name_prefix}-emr-execution-policy"
  role = aws_iam_role.emr_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3DataLakeAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::meridian-atlas-*-${var.environment}",
          "arn:aws:s3:::meridian-atlas-*-${var.environment}/*"
        ]
      },
      {
        Sid    = "GlueAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:BatchCreatePartition",
          "glue:BatchGetPartition"
        ]
        Resource = ["*"]
      },
      {
        Sid    = "KMSAccess"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = [var.kms_key_arn]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/emr-serverless/*"
      }
    ]
  })
}

# ===========================================================================
# CloudWatch Log Group for EMR Serverless
# ===========================================================================

resource "aws_cloudwatch_log_group" "emr_serverless" {
  name              = "/aws/emr-serverless/${var.name_prefix}"
  retention_in_days = 90

  kms_key_id = var.kms_key_arn

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-emr-logs"
    Service = "emr-serverless"
  })
}
