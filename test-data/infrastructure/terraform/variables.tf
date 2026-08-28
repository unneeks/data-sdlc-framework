##############################################################################
# Project ATLAS — Root Input Variables
##############################################################################

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project identifier used in resource naming"
  type        = string
  default     = "meridian-atlas"
}

variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-west-2"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.100.0.0/16"
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones to deploy into"
  type        = list(string)
  default     = ["eu-west-2a", "eu-west-2b", "eu-west-2c"]
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "cost_centre" {
  description = "Cost centre code for billing allocation"
  type        = string
  default     = "CC-4072-ATLAS"
}

variable "owner" {
  description = "Team or individual owning these resources"
  type        = string
  default     = "data-platform-engineering"
}

variable "data_classification" {
  description = "Data classification level for regulatory compliance"
  type        = string
  default     = "Confidential"
  validation {
    condition     = contains(["Public", "Internal", "Confidential", "Restricted"], var.data_classification)
    error_message = "Data classification must be one of: Public, Internal, Confidential, Restricted."
  }
}

# --- Compute Variables ---

variable "emr_spark_version" {
  description = "EMR release label for Spark"
  type        = string
  default     = "emr-7.0.0"
}

variable "emr_max_workers" {
  description = "Maximum number of EMR Serverless workers"
  type        = number
  default     = 50
}

variable "emr_worker_cpu" {
  description = "vCPUs per EMR Serverless worker"
  type        = string
  default     = "4 vCPU"
}

variable "emr_worker_memory" {
  description = "Memory per EMR Serverless worker"
  type        = string
  default     = "16 GB"
}

# --- Streaming Variables ---

variable "msk_broker_instance_type" {
  description = "MSK broker instance type"
  type        = string
  default     = "kafka.m5.large"
}

variable "msk_broker_count" {
  description = "Number of MSK broker nodes (should be multiple of AZ count)"
  type        = number
  default     = 3
}

variable "msk_ebs_volume_size" {
  description = "EBS volume size in GB for each MSK broker"
  type        = number
  default     = 500
}

# --- Monitoring Variables ---

variable "alert_email_endpoints" {
  description = "Email addresses for CloudWatch alarm notifications"
  type        = list(string)
  default     = []
}

variable "pipeline_sla_threshold_minutes" {
  description = "Maximum acceptable pipeline completion time in minutes"
  type        = number
  default     = 60
}

# --- MWAA Variables ---

variable "mwaa_environment_class" {
  description = "MWAA environment class"
  type        = string
  default     = "mw1.medium"
}

variable "mwaa_max_workers" {
  description = "Maximum number of MWAA workers"
  type        = number
  default     = 10
}

# --- Trino/Serving Variables ---

variable "trino_node_count" {
  description = "Number of Trino worker nodes"
  type        = number
  default     = 2
}

variable "trino_instance_type" {
  description = "Instance type for Trino nodes"
  type        = string
  default     = "r6g.xlarge"
}

variable "enable_multi_az" {
  description = "Enable multi-AZ deployment for HA"
  type        = bool
  default     = true
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection on critical resources"
  type        = bool
  default     = false
}
