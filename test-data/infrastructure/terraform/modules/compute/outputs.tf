##############################################################################
# Compute Module — Outputs
##############################################################################

output "emr_application_id" {
  description = "ID of the EMR Serverless application"
  value       = aws_emrserverless_application.spark.id
}

output "emr_application_arn" {
  description = "ARN of the EMR Serverless application"
  value       = aws_emrserverless_application.spark.arn
}

output "emr_execution_role_arn" {
  description = "ARN of the EMR execution IAM role"
  value       = aws_iam_role.emr_execution.arn
}
