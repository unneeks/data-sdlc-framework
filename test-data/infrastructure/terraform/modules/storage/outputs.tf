##############################################################################
# Storage Module — Outputs
##############################################################################

output "bronze_bucket_arn" {
  description = "ARN of the bronze (raw) layer bucket"
  value       = aws_s3_bucket.data_lake["bronze"].arn
}

output "bronze_bucket_name" {
  description = "Name of the bronze (raw) layer bucket"
  value       = aws_s3_bucket.data_lake["bronze"].id
}

output "silver_bucket_arn" {
  description = "ARN of the silver (cleansed) layer bucket"
  value       = aws_s3_bucket.data_lake["silver"].arn
}

output "silver_bucket_name" {
  description = "Name of the silver (cleansed) layer bucket"
  value       = aws_s3_bucket.data_lake["silver"].id
}

output "gold_bucket_arn" {
  description = "ARN of the gold (curated) layer bucket"
  value       = aws_s3_bucket.data_lake["gold"].arn
}

output "gold_bucket_name" {
  description = "Name of the gold (curated) layer bucket"
  value       = aws_s3_bucket.data_lake["gold"].id
}

output "config_bucket_arn" {
  description = "ARN of the config/DAGs bucket"
  value       = aws_s3_bucket.data_lake["config"].arn
}

output "config_bucket_name" {
  description = "Name of the config/DAGs bucket"
  value       = aws_s3_bucket.data_lake["config"].id
}

output "access_logs_bucket_arn" {
  description = "ARN of the access logs bucket"
  value       = aws_s3_bucket.access_logs.arn
}

output "all_bucket_arns" {
  description = "List of all data lake bucket ARNs"
  value       = [for b in aws_s3_bucket.data_lake : b.arn]
}
