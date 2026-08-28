##############################################################################
# Project ATLAS — Monitoring Module
# CloudWatch Dashboards, Metric Alarms, and SNS Alerting
#
# Key SLIs monitored:
# - Pipeline SLA: end-to-end batch completion time
# - Kafka consumer lag: CDC event processing backlog
# - Trino query latency: serving layer response times
# - Cost anomalies: unexpected spend spikes
# - EMR job failures: Spark transformation errors
##############################################################################

# ===========================================================================
# SNS Topics for Alerting
# ===========================================================================

resource "aws_sns_topic" "alerts" {
  name              = "${var.name_prefix}-operational-alerts"
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-operational-alerts"
    Service = "monitoring"
  })
}

resource "aws_sns_topic" "critical_alerts" {
  name              = "${var.name_prefix}-critical-alerts"
  kms_master_key_id = var.kms_key_arn

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-critical-alerts"
    Service = "monitoring"
  })
}

resource "aws_sns_topic_subscription" "alert_email" {
  count = length(var.alert_email_endpoints)

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email_endpoints[count.index]
}

resource "aws_sns_topic_subscription" "critical_alert_email" {
  count = length(var.alert_email_endpoints)

  topic_arn = aws_sns_topic.critical_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email_endpoints[count.index]
}

# ===========================================================================
# CloudWatch Dashboard — Operations Overview
# ===========================================================================

resource "aws_cloudwatch_dashboard" "operations" {
  dashboard_name = "${var.name_prefix}-operations"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 1
        properties = {
          markdown = "# Project ATLAS — Data Platform Operations Dashboard"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 1
        width  = 12
        height = 6
        properties = {
          title   = "MSK — Consumer Group Lag"
          region  = var.region
          metrics = [
            ["AWS/Kafka", "MaxOffsetLag", "Cluster Name", var.msk_cluster_name]
          ]
          period = 300
          stat   = "Maximum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 1
        width  = 12
        height = 6
        properties = {
          title   = "MSK — Bytes In/Out per Sec"
          region  = var.region
          metrics = [
            ["AWS/Kafka", "BytesInPerSec", "Cluster Name", var.msk_cluster_name],
            ["AWS/Kafka", "BytesOutPerSec", "Cluster Name", var.msk_cluster_name]
          ]
          period = 300
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 7
        width  = 12
        height = 6
        properties = {
          title   = "EMR Serverless — Job Run Status"
          region  = var.region
          metrics = [
            ["AWS/EMRServerless", "RunningWorkerCount", "ApplicationId", var.emr_app_id],
            ["AWS/EMRServerless", "IdleWorkerCount", "ApplicationId", var.emr_app_id]
          ]
          period = 60
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 7
        width  = 12
        height = 6
        properties = {
          title   = "MWAA — Task Execution"
          region  = var.region
          metrics = [
            ["AmazonMWAA", "TasksRunning", "Environment", var.mwaa_env_name],
            ["AmazonMWAA", "TasksQueued", "Environment", var.mwaa_env_name],
            ["AmazonMWAA", "TasksFailed", "Environment", var.mwaa_env_name]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 13
        width  = 24
        height = 6
        properties = {
          title   = "Estimated Monthly Cost"
          region  = var.region
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD"]
          ]
          period = 86400
          stat   = "Maximum"
        }
      }
    ]
  })
}

# ===========================================================================
# CloudWatch Alarms — Pipeline SLA
# ===========================================================================

resource "aws_cloudwatch_metric_alarm" "pipeline_sla_breach" {
  alarm_name          = "${var.name_prefix}-pipeline-sla-breach"
  alarm_description   = "Pipeline execution time exceeded SLA threshold of ${var.pipeline_sla_threshold_minutes} minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = var.pipeline_sla_threshold_minutes * 60 # Convert to seconds
  treat_missing_data  = "notBreaching"

  metric_name = "PipelineDurationSeconds"
  namespace   = "ATLAS/Pipeline"
  statistic   = "Maximum"
  period      = 300

  alarm_actions = [aws_sns_topic.critical_alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = merge(var.common_tags, {
    Name     = "${var.name_prefix}-pipeline-sla-alarm"
    Severity = "critical"
  })
}

# ===========================================================================
# CloudWatch Alarms — Kafka Consumer Lag
# ===========================================================================

resource "aws_cloudwatch_metric_alarm" "kafka_consumer_lag" {
  alarm_name          = "${var.name_prefix}-kafka-consumer-lag-high"
  alarm_description   = "Kafka consumer lag exceeds 100,000 messages — CDC processing falling behind"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 100000
  treat_missing_data  = "notBreaching"

  metric_name = "MaxOffsetLag"
  namespace   = "AWS/Kafka"
  statistic   = "Maximum"
  period      = 300
  dimensions = {
    "Cluster Name" = var.msk_cluster_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = merge(var.common_tags, {
    Name     = "${var.name_prefix}-kafka-lag-alarm"
    Severity = "warning"
  })
}

resource "aws_cloudwatch_metric_alarm" "kafka_consumer_lag_critical" {
  alarm_name          = "${var.name_prefix}-kafka-consumer-lag-critical"
  alarm_description   = "Kafka consumer lag exceeds 1,000,000 messages — severe processing backlog"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 1000000
  treat_missing_data  = "notBreaching"

  metric_name = "MaxOffsetLag"
  namespace   = "AWS/Kafka"
  statistic   = "Maximum"
  period      = 300
  dimensions = {
    "Cluster Name" = var.msk_cluster_name
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = merge(var.common_tags, {
    Name     = "${var.name_prefix}-kafka-lag-critical-alarm"
    Severity = "critical"
  })
}

# ===========================================================================
# CloudWatch Alarms — Trino Query Latency
# ===========================================================================

resource "aws_cloudwatch_metric_alarm" "trino_latency" {
  alarm_name          = "${var.name_prefix}-trino-query-latency-high"
  alarm_description   = "Trino p95 query latency exceeds 30 seconds"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 30000 # 30 seconds in milliseconds
  treat_missing_data  = "notBreaching"

  metric_name = "QueryLatencyP95"
  namespace   = "ATLAS/Trino"
  statistic   = "Maximum"
  period      = 300

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = merge(var.common_tags, {
    Name     = "${var.name_prefix}-trino-latency-alarm"
    Severity = "warning"
  })
}

# ===========================================================================
# CloudWatch Alarms — Cost Anomaly
# ===========================================================================

resource "aws_cloudwatch_metric_alarm" "cost_anomaly" {
  alarm_name          = "${var.name_prefix}-cost-anomaly"
  alarm_description   = "Daily estimated charges exceeded expected threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 5000 # USD daily threshold — adjust per environment
  treat_missing_data  = "notBreaching"

  metric_name = "EstimatedCharges"
  namespace   = "AWS/Billing"
  statistic   = "Maximum"
  period      = 86400
  dimensions = {
    Currency = "USD"
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = merge(var.common_tags, {
    Name     = "${var.name_prefix}-cost-alarm"
    Severity = "warning"
  })
}

# ===========================================================================
# CloudWatch Alarms — EMR Serverless Job Failures
# ===========================================================================

resource "aws_cloudwatch_metric_alarm" "emr_job_failures" {
  alarm_name          = "${var.name_prefix}-emr-job-failures"
  alarm_description   = "EMR Serverless Spark jobs are failing"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0
  treat_missing_data  = "notBreaching"

  metric_name = "FailedJobCount"
  namespace   = "ATLAS/EMR"
  statistic   = "Sum"
  period      = 300

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = merge(var.common_tags, {
    Name     = "${var.name_prefix}-emr-failures-alarm"
    Severity = "critical"
  })
}

# ===========================================================================
# CloudWatch Alarms — MSK Disk Usage
# ===========================================================================

resource "aws_cloudwatch_metric_alarm" "msk_disk_usage" {
  alarm_name          = "${var.name_prefix}-msk-disk-usage-high"
  alarm_description   = "MSK broker disk usage exceeds 75%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 75
  treat_missing_data  = "notBreaching"

  metric_name = "KafkaDataLogsDiskUsed"
  namespace   = "AWS/Kafka"
  statistic   = "Maximum"
  period      = 300
  dimensions = {
    "Cluster Name" = var.msk_cluster_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(var.common_tags, {
    Name     = "${var.name_prefix}-msk-disk-alarm"
    Severity = "warning"
  })
}
