##############################################################################
# Project ATLAS — Streaming Module
# Amazon MSK Cluster for CDC (Change Data Capture) event streaming
#
# Architecture:
# - Oracle GoldenGate / Debezium captures DML changes from Oracle DWH
# - Events published to MSK topics per source table
# - Spark Structured Streaming (EMR) consumes from MSK into Bronze layer
#
# Security:
# - IAM authentication (no SASL/SCRAM credentials to manage)
# - TLS encryption in transit between brokers and clients
# - KMS encryption at rest for EBS volumes
# - Private subnets only — no public access
##############################################################################

# ===========================================================================
# MSK Cluster Configuration
# ===========================================================================

resource "aws_msk_configuration" "atlas" {
  name              = "${var.name_prefix}-msk-config"
  kafka_versions    = ["3.6.0"]
  description       = "ATLAS CDC streaming configuration"

  server_properties = <<-PROPERTIES
    auto.create.topics.enable=false
    default.replication.factor=3
    min.insync.replicas=2
    num.partitions=6
    num.io.threads=8
    num.network.threads=5
    num.replica.fetchers=2
    replica.lag.time.max.ms=30000
    socket.receive.buffer.bytes=102400
    socket.request.max.bytes=104857600
    socket.send.buffer.bytes=102400
    unclean.leader.election.enable=false
    log.retention.hours=168
    log.retention.bytes=-1
    log.segment.bytes=1073741824
    log.cleanup.policy=delete
    message.max.bytes=10485760
  PROPERTIES

  tags = var.common_tags
}

# ===========================================================================
# MSK Cluster
# ===========================================================================

resource "aws_msk_cluster" "atlas" {
  cluster_name           = "${var.name_prefix}-msk"
  kafka_version          = "3.6.0"
  number_of_broker_nodes = var.msk_broker_count

  configuration_info {
    arn      = aws_msk_configuration.atlas.arn
    revision = aws_msk_configuration.atlas.latest_revision
  }

  broker_node_group_info {
    instance_type   = var.msk_instance_type
    client_subnets  = slice(var.private_subnet_ids, 0, min(length(var.private_subnet_ids), var.msk_broker_count))
    security_groups = [var.security_group_id]

    storage_info {
      ebs_storage_info {
        volume_size = var.msk_ebs_volume_size

        provisioned_throughput {
          enabled           = var.msk_ebs_volume_size >= 500
          volume_throughput = var.msk_ebs_volume_size >= 500 ? 250 : null
        }
      }
    }

    connectivity_info {
      public_access {
        type = "DISABLED"
      }
    }
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = var.kms_key_arn

    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  client_authentication {
    unauthenticated = false

    sasl {
      iam   = true
      scram = false
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }

      s3 {
        enabled = true
        bucket  = aws_s3_bucket.msk_logs.id
        prefix  = "broker-logs"
      }
    }
  }

  enhanced_monitoring = "PER_TOPIC_PER_BROKER"

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-msk"
    Service = "msk"
  })
}

# ===========================================================================
# MSK Broker Logs
# ===========================================================================

resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${var.name_prefix}"
  retention_in_days = 30

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-msk-logs"
    Service = "msk"
  })
}

resource "aws_s3_bucket" "msk_logs" {
  bucket = "${var.name_prefix}-msk-logs"

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-msk-logs"
    Service = "msk"
  })
}

resource "aws_s3_bucket_public_access_block" "msk_logs" {
  bucket = aws_s3_bucket.msk_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "msk_logs" {
  bucket = aws_s3_bucket.msk_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "msk_logs" {
  bucket = aws_s3_bucket.msk_logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 90
    }
  }
}

# ===========================================================================
# MSK Serverless Topics (defined as documentation — actual topic creation
# should happen via Kafka CLI or application bootstrap scripts)
#
# Topics for CDC events:
# - atlas.cdc.core-banking.accounts
# - atlas.cdc.core-banking.transactions
# - atlas.cdc.core-banking.customers
# - atlas.cdc.core-banking.products
# - atlas.cdc.risk.positions
# - atlas.cdc.risk.exposures
# - atlas.cdc.payments.instructions
# - atlas.cdc.payments.settlements
# - atlas.pipeline.dead-letter
# - atlas.pipeline.audit-events
# ===========================================================================
