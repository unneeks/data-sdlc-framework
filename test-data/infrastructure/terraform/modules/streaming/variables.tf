##############################################################################
# Streaming Module — Input Variables
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

variable "msk_broker_count" {
  description = "Number of MSK broker nodes"
  type        = number
}

variable "msk_instance_type" {
  description = "MSK broker instance type"
  type        = string
}

variable "msk_ebs_volume_size" {
  description = "EBS volume size per broker in GB"
  type        = number
}

variable "enable_multi_az" {
  description = "Enable multi-AZ deployment"
  type        = bool
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
  description = "Security group ID for MSK brokers"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for MSK encryption"
  type        = string
}
