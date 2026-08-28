##############################################################################
# Project ATLAS — Production Environment Configuration
# High availability, multi-AZ, larger instances, strict protection
##############################################################################

environment        = "prod"
project_name       = "meridian-atlas"
region             = "eu-west-2"
vpc_cidr           = "10.200.0.0/16"
availability_zones = ["eu-west-2a", "eu-west-2b", "eu-west-2c"]

# --- Tagging ---
cost_centre         = "CC-4072-ATLAS"
owner               = "data-platform-engineering"
data_classification = "Restricted"

tags = {
  Tier             = "production"
  AutoShutdown     = "false"
  ComplianceScope  = "PCI-DSS"
  DisasterRecovery = "active-passive"
}

# --- Compute (EMR Serverless) ---
emr_spark_version = "emr-7.0.0"
emr_max_workers   = 100
emr_worker_cpu    = "8 vCPU"
emr_worker_memory = "32 GB"

# --- Streaming (MSK) ---
msk_broker_instance_type = "kafka.m5.2xlarge"
msk_broker_count         = 6
msk_ebs_volume_size      = 2000

# --- Orchestration (MWAA) ---
mwaa_environment_class = "mw1.large"
mwaa_max_workers       = 25

# --- Serving (Trino) ---
trino_node_count    = 6
trino_instance_type = "r6g.4xlarge"

# --- Monitoring ---
alert_email_endpoints          = ["atlas-prod-alerts@meridianbank.com", "sre-oncall@meridianbank.com"]
pipeline_sla_threshold_minutes = 45

# --- HA / Protection ---
enable_multi_az            = true
enable_deletion_protection = true
