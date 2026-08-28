##############################################################################
# Project ATLAS — Root Module Outputs
##############################################################################

# --- Networking ---

output "vpc_id" {
  description = "ID of the project VPC"
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.networking.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets (NAT gateway hosting only)"
  value       = module.networking.public_subnet_ids
}

# --- Storage ---

output "s3_bucket_arns" {
  description = "ARNs of the data lake S3 buckets (bronze, silver, gold, config)"
  value = {
    bronze = module.storage.bronze_bucket_arn
    silver = module.storage.silver_bucket_arn
    gold   = module.storage.gold_bucket_arn
    config = module.storage.config_bucket_arn
  }
}

output "s3_bucket_names" {
  description = "Names of the data lake S3 buckets"
  value = {
    bronze = module.storage.bronze_bucket_name
    silver = module.storage.silver_bucket_name
    gold   = module.storage.gold_bucket_name
    config = module.storage.config_bucket_name
  }
}

# --- Streaming ---

output "msk_cluster_arn" {
  description = "ARN of the MSK cluster for CDC streaming"
  value       = module.streaming.msk_cluster_arn
}

output "msk_bootstrap_brokers" {
  description = "MSK bootstrap broker connection string (IAM auth)"
  value       = module.streaming.msk_bootstrap_brokers_iam
  sensitive   = true
}

# --- Orchestration ---

output "mwaa_env_arn" {
  description = "ARN of the MWAA (Airflow) environment"
  value       = module.orchestration.mwaa_environment_arn
}

output "mwaa_webserver_url" {
  description = "URL of the MWAA Airflow web UI"
  value       = module.orchestration.mwaa_webserver_url
}

# --- Compute ---

output "emr_app_id" {
  description = "ID of the EMR Serverless application"
  value       = module.compute.emr_application_id
}

output "emr_app_arn" {
  description = "ARN of the EMR Serverless application"
  value       = module.compute.emr_application_arn
}

# --- Serving ---

output "trino_endpoint" {
  description = "Endpoint for Trino query access"
  value       = module.serving.trino_endpoint
}

# --- Security ---

output "kms_key_arns" {
  description = "ARNs of KMS keys used for encryption"
  value = {
    s3         = module.security.s3_kms_key_arn
    msk        = module.security.msk_kms_key_arn
    emr        = module.security.emr_kms_key_arn
    mwaa       = module.security.mwaa_kms_key_arn
    monitoring = module.security.monitoring_kms_key_arn
  }
}

# --- Monitoring ---

output "sns_alert_topic_arn" {
  description = "ARN of the SNS topic for operational alerts"
  value       = module.monitoring.sns_alert_topic_arn
}

output "cloudwatch_dashboard_url" {
  description = "URL to the CloudWatch operations dashboard"
  value       = module.monitoring.dashboard_url
}
