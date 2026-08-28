##############################################################################
# Project ATLAS — Storage Module
# S3 Buckets for the medallion architecture (Bronze/Silver/Gold/Config)
#
# Security posture for regulated banking:
# - SSE-KMS encryption with customer-managed keys
# - Versioning enabled on all buckets
# - Public access blocked at bucket level
# - Lifecycle policies for cost management and data retention
# - Access logging enabled
##############################################################################

locals {
  bucket_layers = {
    bronze = {
      name                     = "meridian-atlas-bronze-${var.environment}"
      transition_to_ia_days    = 90
      transition_to_glacier_days = 365
      expiration_days          = 2555 # 7 years for regulatory retention
      noncurrent_expiration    = 90
    }
    silver = {
      name                     = "meridian-atlas-silver-${var.environment}"
      transition_to_ia_days    = 180
      transition_to_glacier_days = 730
      expiration_days          = 2555
      noncurrent_expiration    = 60
    }
    gold = {
      name                     = "meridian-atlas-gold-${var.environment}"
      transition_to_ia_days    = 365
      transition_to_glacier_days = null # Gold data stays accessible
      expiration_days          = null   # No expiration for serving layer
      noncurrent_expiration    = 30
    }
    config = {
      name                     = "meridian-atlas-config-${var.environment}"
      transition_to_ia_days    = null
      transition_to_glacier_days = null
      expiration_days          = null
      noncurrent_expiration    = 30
    }
  }
}

# ===========================================================================
# S3 Buckets
# ===========================================================================

resource "aws_s3_bucket" "data_lake" {
  for_each = local.bucket_layers

  bucket        = each.value.name
  force_destroy = var.environment != "prod" ? true : false

  tags = merge(var.common_tags, {
    Name      = each.value.name
    DataLayer = each.key
  })
}

# ===========================================================================
# Versioning
# ===========================================================================

resource "aws_s3_bucket_versioning" "data_lake" {
  for_each = local.bucket_layers

  bucket = aws_s3_bucket.data_lake[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

# ===========================================================================
# Server-Side Encryption — KMS CMK
# ===========================================================================

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  for_each = local.bucket_layers

  bucket = aws_s3_bucket.data_lake[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

# ===========================================================================
# Block Public Access — Mandatory for banking
# ===========================================================================

resource "aws_s3_bucket_public_access_block" "data_lake" {
  for_each = local.bucket_layers

  bucket = aws_s3_bucket.data_lake[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ===========================================================================
# Lifecycle Policies
# ===========================================================================

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  for_each = {
    for k, v in local.bucket_layers : k => v
    if v.transition_to_ia_days != null || v.expiration_days != null
  }

  bucket = aws_s3_bucket.data_lake[each.key].id

  rule {
    id     = "tiered-storage-${each.key}"
    status = "Enabled"

    filter {
      prefix = ""
    }

    dynamic "transition" {
      for_each = each.value.transition_to_ia_days != null ? [1] : []
      content {
        days          = each.value.transition_to_ia_days
        storage_class = "STANDARD_IA"
      }
    }

    dynamic "transition" {
      for_each = each.value.transition_to_glacier_days != null ? [1] : []
      content {
        days          = each.value.transition_to_glacier_days
        storage_class = "GLACIER"
      }
    }

    dynamic "expiration" {
      for_each = each.value.expiration_days != null ? [1] : []
      content {
        days = each.value.expiration_days
      }
    }

    noncurrent_version_expiration {
      noncurrent_days = each.value.noncurrent_expiration
    }
  }

  rule {
    id     = "abort-incomplete-multipart-${each.key}"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.data_lake]
}

# ===========================================================================
# Bucket Policy — Enforce encryption in transit (TLS)
# ===========================================================================

resource "aws_s3_bucket_policy" "enforce_tls" {
  for_each = local.bucket_layers

  bucket = aws_s3_bucket.data_lake[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.data_lake[each.key].arn,
          "${aws_s3_bucket.data_lake[each.key].arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid       = "DenyIncorrectEncryptionHeader"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.data_lake[each.key].arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.data_lake]
}

# ===========================================================================
# Access Logging
# ===========================================================================

resource "aws_s3_bucket" "access_logs" {
  bucket = "meridian-atlas-access-logs-${var.environment}"

  tags = merge(var.common_tags, {
    Name      = "meridian-atlas-access-logs-${var.environment}"
    DataLayer = "logging"
  })
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 365
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_logging" "data_lake" {
  for_each = local.bucket_layers

  bucket = aws_s3_bucket.data_lake[each.key].id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "${each.key}/"
}
