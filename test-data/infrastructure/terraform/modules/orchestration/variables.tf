##############################################################################
# Orchestration Module — Input Variables
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

variable "mwaa_environment_class" {
  description = "MWAA environment class"
  type        = string
}

variable "mwaa_max_workers" {
  description = "Maximum number of MWAA workers"
  type        = number
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
  description = "Security group ID for MWAA"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for MWAA encryption"
  type        = string
}

variable "dags_bucket_arn" {
  description = "ARN of the S3 bucket containing DAG files"
  type        = string
}

variable "dags_bucket_name" {
  description = "Name of the S3 bucket containing DAG files"
  type        = string
}
