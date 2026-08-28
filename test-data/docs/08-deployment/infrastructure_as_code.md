# Infrastructure as Code — Project ATLAS

## Principles

1. **All infrastructure is codified** — no manual console changes permitted in any environment
2. **State is remote and locked** — Terraform state stored in S3 with DynamoDB locking
3. **Environments are identical** — same modules, different variables (tfvars)
4. **Drift detection is automated** — weekly `terraform plan` runs flag unmanaged resources

## Terraform State Management

| Item | Value |
|------|-------|
| Backend | S3 (`meridian-atlas-tfstate-{env}`) |
| Locking | DynamoDB (`atlas-terraform-locks`) |
| State encryption | KMS CMK (per-environment) |
| Workspace strategy | One workspace per environment |

## Module Registry

| Module | Version | Purpose |
|--------|---------|---------|
| `networking` | 2.1.0 | VPC, subnets (3 AZs), NAT gateways, VPC endpoints |
| `storage` | 1.4.0 | S3 buckets (bronze/silver/gold), lifecycle, replication |
| `compute` | 1.3.0 | EMR Serverless applications, security configs |
| `orchestration` | 1.2.0 | MWAA environment, DAG S3 bucket, execution role |
| `streaming` | 1.1.0 | MSK cluster, topics, Schema Registry |
| `serving` | 1.0.0 | EKS cluster for Trino, node groups, HPA |
| `monitoring` | 1.2.0 | CloudWatch dashboards, alarms, SNS topics |
| `security` | 2.0.0 | IAM roles, KMS keys, Secrets Manager entries |

## Tagging Strategy

All resources are tagged for cost allocation and governance:

```hcl
locals {
  common_tags = {
    Project     = "ATLAS"
    Environment = var.environment
    ManagedBy   = "Terraform"
    CostCentre  = "DATA-PLATFORM-001"
    Owner       = "data-engineering@meridian.bank"
    Compliance  = "SOX,PCI-DSS"
  }
}
```

## Cost Controls

| Mechanism | Implementation |
|-----------|---------------|
| Budget alerts | AWS Budgets: 80%, 100%, 120% threshold notifications |
| Spot/Savings Plans | EMR Serverless uses spot capacity; reserved for MSK/EKS |
| Auto-shutdown (non-prod) | EventBridge rule stops dev resources outside 07:00–19:00 UTC |
| Right-sizing | Monthly review via AWS Compute Optimizer |
| S3 lifecycle | Bronze: Glacier after 365d; Silver/Gold: IA after 90d |
