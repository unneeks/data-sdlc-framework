##############################################################################
# Project ATLAS — Dev Environment Configuration
# Minimal resources for development and testing
##############################################################################

environment        = "dev"
project_name       = "meridian-atlas"
region             = "eu-west-2"
vpc_cidr           = "10.100.0.0/16"
availability_zones = ["eu-west-2a", "eu-west-2b", "eu-west-2c"]

# --- Tagging ---
cost_centre         = "CC-4072-ATLAS"
owner               = "data-platform-engineering"
data_classification = "Confidential"

tags = {
  Tier        = "development"
  AutoShutdown = "true"
}

# --- Compute (EMR Serverless) ---
emr_spark_version = "emr-7.0.0"
emr_max_workers   = 10
emr_worker_cpu    = "4 vCPU"
emr_worker_memory = "16 GB"

# --- Streaming (MSK) ---
msk_broker_instance_type = "kafka.m5.large"
msk_broker_count         = 3
msk_ebs_volume_size      = 100

# --- Orchestration (MWAA) ---
mwaa_environment_class = "mw1.small"
mwaa_max_workers       = 5

# --- Serving (Trino) ---
trino_node_count    = 1
trino_instance_type = "r6g.large"

# --- Monitoring ---
alert_email_endpoints          = ["atlas-dev-alerts@meridianbank.com"]
pipeline_sla_threshold_minutes = 120

# --- HA / Protection ---
enable_multi_az            = false
enable_deletion_protection = false
