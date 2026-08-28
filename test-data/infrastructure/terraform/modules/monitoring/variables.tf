##############################################################################
# Monitoring Module — Input Variables
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

variable "alert_email_endpoints" {
  description = "Email addresses for alarm notifications"
  type        = list(string)
}

variable "pipeline_sla_threshold_minutes" {
  description = "Maximum acceptable pipeline completion time in minutes"
  type        = number
}

variable "msk_cluster_name" {
  description = "Name of the MSK cluster (for alarm dimensions)"
  type        = string
}

variable "msk_cluster_arn" {
  description = "ARN of the MSK cluster"
  type        = string
}

variable "emr_app_id" {
  description = "EMR Serverless application ID"
  type        = string
}

variable "mwaa_env_name" {
  description = "Name of the MWAA environment"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encrypting SNS topics"
  type        = string
}
