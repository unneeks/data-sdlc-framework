##############################################################################
# Streaming Module — Outputs
##############################################################################

output "msk_cluster_arn" {
  description = "ARN of the MSK cluster"
  value       = aws_msk_cluster.atlas.arn
}

output "msk_cluster_name" {
  description = "Name of the MSK cluster"
  value       = aws_msk_cluster.atlas.cluster_name
}

output "msk_bootstrap_brokers_iam" {
  description = "MSK bootstrap broker string for IAM authentication"
  value       = aws_msk_cluster.atlas.bootstrap_brokers_sasl_iam
}

output "msk_zookeeper_connect" {
  description = "MSK Zookeeper connection string"
  value       = aws_msk_cluster.atlas.zookeeper_connect_string
}

output "msk_configuration_arn" {
  description = "ARN of the MSK cluster configuration"
  value       = aws_msk_configuration.atlas.arn
}
