##############################################################################
# Serving Module — Outputs
##############################################################################

output "trino_endpoint" {
  description = "Internal DNS endpoint for Trino coordinator"
  value       = "coordinator.trino.${var.name_prefix}.internal:8443"
}

output "trino_cluster_id" {
  description = "ECS cluster ID for Trino"
  value       = aws_ecs_cluster.trino.id
}

output "trino_coordinator_service_name" {
  description = "ECS service name for Trino coordinator"
  value       = aws_ecs_service.trino_coordinator.name
}

output "trino_worker_service_name" {
  description = "ECS service name for Trino workers"
  value       = aws_ecs_service.trino_worker.name
}
