##############################################################################
# Storage Module — Input Variables
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

variable "kms_key_arn" {
  description = "ARN of the KMS key for S3 encryption"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "enable_deletion_protection" {
  description = "Prevent accidental bucket deletion in production"
  type        = bool
  default     = false
}
