##############################################################################
# Orchestration Module — Outputs
##############################################################################

output "mwaa_environment_arn" {
  description = "ARN of the MWAA environment"
  value       = aws_mwaa_environment.atlas.arn
}

output "mwaa_environment_name" {
  description = "Name of the MWAA environment"
  value       = aws_mwaa_environment.atlas.name
}

output "mwaa_webserver_url" {
  description = "URL of the MWAA Airflow web UI"
  value       = aws_mwaa_environment.atlas.webserver_url
}

output "mwaa_execution_role_arn" {
  description = "ARN of the MWAA execution role"
  value       = aws_iam_role.mwaa_execution.arn
}
