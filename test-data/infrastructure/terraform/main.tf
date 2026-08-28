##############################################################################
# Project ATLAS — Root Module
# Banking Data Platform Migration (Oracle DWH → AWS Lakehouse)
#
# This root module orchestrates child modules for the complete data platform
# infrastructure. All resources are deployed in private subnets with
# encryption at rest and in transit, per regulatory requirements.
##############################################################################

locals {
  common_tags = merge(
    {
      Project            = var.project_name
      Environment        = var.environment
      ManagedBy          = "terraform"
      CostCentre         = var.cost_centre
      Owner              = var.owner
      DataClassification = var.data_classification
    },
    var.tags
  )

  name_prefix = "${var.project_name}-${var.environment}"
}

# --- Data Sources ---

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

# ===========================================================================
# Networking — VPC, Subnets, NAT Gateways, VPC Endpoints
# ===========================================================================

module "networking" {
  source = "./modules/networking"

  environment        = var.environment
  project_name       = var.project_name
  region             = var.region
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  common_tags        = local.common_tags
  name_prefix        = local.name_prefix
}

# ===========================================================================
# Security — KMS Keys, IAM Roles, Security Groups
# ===========================================================================

module "security" {
  source = "./modules/security"

  environment    = var.environment
  project_name   = var.project_name
  region         = var.region
  common_tags    = local.common_tags
  name_prefix    = local.name_prefix
  vpc_id         = module.networking.vpc_id
  vpc_cidr       = var.vpc_cidr
  account_id     = data.aws_caller_identity.current.account_id
}

# ===========================================================================
# Storage — S3 Buckets (Bronze/Silver/Gold/Config), Lifecycle, KMS
# ===========================================================================

module "storage" {
  source = "./modules/storage"

  environment  = var.environment
  project_name = var.project_name
  region       = var.region
  common_tags  = local.common_tags
  name_prefix  = local.name_prefix
  kms_key_arn  = module.security.s3_kms_key_arn
  account_id   = data.aws_caller_identity.current.account_id

  enable_deletion_protection = var.enable_deletion_protection
}

# ===========================================================================
# Compute — EMR Serverless (Spark) for batch transformations
# ===========================================================================

module "compute" {
  source = "./modules/compute"

  environment       = var.environment
  project_name      = var.project_name
  region            = var.region
  common_tags       = local.common_tags
  name_prefix       = local.name_prefix
  emr_spark_version = var.emr_spark_version
  emr_max_workers   = var.emr_max_workers
  emr_worker_cpu    = var.emr_worker_cpu
  emr_worker_memory = var.emr_worker_memory

  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  security_group_id  = module.security.emr_security_group_id
  kms_key_arn        = module.security.emr_kms_key_arn
}

# ===========================================================================
# Streaming — MSK Cluster for CDC event streaming
# ===========================================================================

module "streaming" {
  source = "./modules/streaming"

  environment           = var.environment
  project_name          = var.project_name
  region                = var.region
  common_tags           = local.common_tags
  name_prefix           = local.name_prefix
  msk_broker_count      = var.msk_broker_count
  msk_instance_type     = var.msk_broker_instance_type
  msk_ebs_volume_size   = var.msk_ebs_volume_size
  enable_multi_az       = var.enable_multi_az

  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  security_group_id  = module.security.msk_security_group_id
  kms_key_arn        = module.security.msk_kms_key_arn
}

# ===========================================================================
# Orchestration — MWAA (Managed Airflow) for pipeline scheduling
# ===========================================================================

module "orchestration" {
  source = "./modules/orchestration"

  environment          = var.environment
  project_name         = var.project_name
  region               = var.region
  common_tags          = local.common_tags
  name_prefix          = local.name_prefix
  mwaa_environment_class = var.mwaa_environment_class
  mwaa_max_workers     = var.mwaa_max_workers

  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  security_group_id  = module.security.mwaa_security_group_id
  kms_key_arn        = module.security.mwaa_kms_key_arn
  dags_bucket_arn    = module.storage.config_bucket_arn
  dags_bucket_name   = module.storage.config_bucket_name
}

# ===========================================================================
# Serving — Trino query engine for the lakehouse serving layer
# ===========================================================================

module "serving" {
  source = "./modules/serving"

  environment      = var.environment
  project_name     = var.project_name
  region           = var.region
  common_tags      = local.common_tags
  name_prefix      = local.name_prefix
  trino_node_count   = var.trino_node_count
  trino_instance_type = var.trino_instance_type

  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  security_group_id  = module.security.trino_security_group_id
}

# ===========================================================================
# Monitoring — CloudWatch Dashboards, Alarms, SNS Alerting
# ===========================================================================

module "monitoring" {
  source = "./modules/monitoring"

  environment                    = var.environment
  project_name                   = var.project_name
  region                         = var.region
  common_tags                    = local.common_tags
  name_prefix                    = local.name_prefix
  alert_email_endpoints          = var.alert_email_endpoints
  pipeline_sla_threshold_minutes = var.pipeline_sla_threshold_minutes

  msk_cluster_name = module.streaming.msk_cluster_name
  msk_cluster_arn  = module.streaming.msk_cluster_arn
  emr_app_id       = module.compute.emr_application_id
  mwaa_env_name    = module.orchestration.mwaa_environment_name
  kms_key_arn      = module.security.monitoring_kms_key_arn
}
