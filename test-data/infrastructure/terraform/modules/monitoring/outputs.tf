##############################################################################
# Monitoring Module — Outputs
##############################################################################

output "sns_alert_topic_arn" {
  description = "ARN of the operational alerts SNS topic"
  value       = aws_sns_topic.alerts.arn
}

output "sns_critical_alert_topic_arn" {
  description = "ARN of the critical alerts SNS topic"
  value       = aws_sns_topic.critical_alerts.arn
}

output "dashboard_url" {
  description = "URL to the CloudWatch operations dashboard"
  value       = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${var.name_prefix}-operations"
}
