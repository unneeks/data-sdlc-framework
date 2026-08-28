##############################################################################
# Project ATLAS — Security Module
# KMS Keys, IAM Roles, Security Groups
#
# Banking-grade security requirements:
# - Dedicated KMS CMKs per service (separation of duties)
# - Key rotation enabled on all keys
# - Least-privilege security groups
# - No inbound from 0.0.0.0/0 on any security group
##############################################################################

# ===========================================================================
# KMS Keys — One per service for blast-radius containment
# ===========================================================================

resource "aws_kms_key" "s3" {
  description             = "ATLAS S3 data lake encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = false

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "S3ServiceAccess"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-kms-s3"
    Service = "s3"
  })
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${var.name_prefix}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

resource "aws_kms_key" "msk" {
  description             = "ATLAS MSK encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "MSKServiceAccess"
        Effect = "Allow"
        Principal = {
          Service = "kafka.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-kms-msk"
    Service = "msk"
  })
}

resource "aws_kms_alias" "msk" {
  name          = "alias/${var.name_prefix}-msk"
  target_key_id = aws_kms_key.msk.key_id
}

resource "aws_kms_key" "emr" {
  description             = "ATLAS EMR Serverless encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "EMRServiceAccess"
        Effect = "Allow"
        Principal = {
          Service = "emr-serverless.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-kms-emr"
    Service = "emr"
  })
}

resource "aws_kms_alias" "emr" {
  name          = "alias/${var.name_prefix}-emr"
  target_key_id = aws_kms_key.emr.key_id
}

resource "aws_kms_key" "mwaa" {
  description             = "ATLAS MWAA encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "MWAAServiceAccess"
        Effect = "Allow"
        Principal = {
          Service = "airflow.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-kms-mwaa"
    Service = "mwaa"
  })
}

resource "aws_kms_alias" "mwaa" {
  name          = "alias/${var.name_prefix}-mwaa"
  target_key_id = aws_kms_key.mwaa.key_id
}

resource "aws_kms_key" "monitoring" {
  description             = "ATLAS monitoring/SNS encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "SNSServiceAccess"
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchAccess"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-kms-monitoring"
    Service = "monitoring"
  })
}

resource "aws_kms_alias" "monitoring" {
  name          = "alias/${var.name_prefix}-monitoring"
  target_key_id = aws_kms_key.monitoring.key_id
}

# ===========================================================================
# Security Groups
# ===========================================================================

# --- EMR Serverless Security Group ---
resource "aws_security_group" "emr" {
  name_prefix = "${var.name_prefix}-emr-"
  description = "Security group for EMR Serverless workers"
  vpc_id      = var.vpc_id

  # EMR workers communicate with each other
  ingress {
    description = "EMR inter-node communication"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "Allow all outbound (NAT gateway for AWS APIs)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-emr-sg"
    Service = "emr"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# --- MSK Security Group ---
resource "aws_security_group" "msk" {
  name_prefix = "${var.name_prefix}-msk-"
  description = "Security group for MSK brokers"
  vpc_id      = var.vpc_id

  # Kafka broker port (TLS)
  ingress {
    description = "Kafka TLS from VPC"
    from_port   = 9098
    to_port     = 9098
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # Kafka inter-broker replication
  ingress {
    description = "Inter-broker replication"
    from_port   = 9098
    to_port     = 9098
    protocol    = "tcp"
    self        = true
  }

  # Zookeeper
  ingress {
    description = "Zookeeper from VPC"
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-msk-sg"
    Service = "msk"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# --- MWAA Security Group ---
resource "aws_security_group" "mwaa" {
  name_prefix = "${var.name_prefix}-mwaa-"
  description = "Security group for MWAA environment"
  vpc_id      = var.vpc_id

  ingress {
    description = "MWAA self-referencing (required)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "Allow all outbound (AWS APIs via NAT/VPC endpoints)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-mwaa-sg"
    Service = "mwaa"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# --- Trino Security Group ---
resource "aws_security_group" "trino" {
  name_prefix = "${var.name_prefix}-trino-"
  description = "Security group for Trino cluster"
  vpc_id      = var.vpc_id

  # Trino HTTP port
  ingress {
    description = "Trino HTTPS from VPC"
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # Trino inter-node communication
  ingress {
    description = "Trino inter-node"
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    self        = true
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-trino-sg"
    Service = "trino"
  })

  lifecycle {
    create_before_destroy = true
  }
}
