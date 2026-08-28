##############################################################################
# Compute Module — Input Variables
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

variable "emr_spark_version" {
  description = "EMR release label for Spark"
  type        = string
}

variable "emr_max_workers" {
  description = "Maximum number of EMR Serverless workers"
  type        = number
}

variable "emr_worker_cpu" {
  description = "vCPUs per EMR Serverless worker"
  type        = string
}

variable "emr_worker_memory" {
  description = "Memory per EMR Serverless worker"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of the private subnets for EMR networking"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for EMR Serverless"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for EMR encryption"
  type        = string
}
