##############################################################################
# Serving Module — Input Variables
##############################################################################

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "project_name" {
  description = "Project identifier"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
}

variable "name_prefix" {
  description = "Naming prefix for resources"
  type        = string
}

variable "trino_node_count" {
  description = "Number of Trino worker nodes"
  type        = number
}

variable "trino_instance_type" {
  description = "Instance type for Trino nodes (used for Fargate CPU/memory mapping)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of the private subnets"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for Trino"
  type        = string
}
