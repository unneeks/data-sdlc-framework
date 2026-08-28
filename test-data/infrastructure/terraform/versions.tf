##############################################################################
# Project ATLAS — Terraform Version Constraints & Backend Configuration
# Banking Data Platform Migration (Oracle DWH → AWS Lakehouse)
##############################################################################

terraform {
  required_version = ">= 1.7.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket         = "meridian-atlas-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    dynamodb_table = "meridian-atlas-terraform-locks"
    kms_key_id     = "alias/meridian-atlas-terraform-state-key"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.common_tags
  }
}

provider "kubernetes" {
  # Configured via EKS cluster auth when compute module provisions EKS
  config_path = "~/.kube/config"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}
