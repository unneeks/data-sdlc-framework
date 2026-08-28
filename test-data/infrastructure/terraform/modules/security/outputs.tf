##############################################################################
# Security Module — Outputs
##############################################################################

# --- KMS Keys ---

output "s3_kms_key_arn" {
  description = "ARN of the S3 KMS key"
  value       = aws_kms_key.s3.arn
}

output "msk_kms_key_arn" {
  description = "ARN of the MSK KMS key"
  value       = aws_kms_key.msk.arn
}

output "emr_kms_key_arn" {
  description = "ARN of the EMR KMS key"
  value       = aws_kms_key.emr.arn
}

output "mwaa_kms_key_arn" {
  description = "ARN of the MWAA KMS key"
  value       = aws_kms_key.mwaa.arn
}

output "monitoring_kms_key_arn" {
  description = "ARN of the monitoring/SNS KMS key"
  value       = aws_kms_key.monitoring.arn
}

# --- Security Groups ---

output "emr_security_group_id" {
  description = "Security group ID for EMR Serverless"
  value       = aws_security_group.emr.id
}

output "msk_security_group_id" {
  description = "Security group ID for MSK brokers"
  value       = aws_security_group.msk.id
}

output "mwaa_security_group_id" {
  description = "Security group ID for MWAA"
  value       = aws_security_group.mwaa.id
}

output "trino_security_group_id" {
  description = "Security group ID for Trino"
  value       = aws_security_group.trino.id
}
