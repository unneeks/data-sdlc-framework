##############################################################################
# Project ATLAS — Serving Module
# Trino query engine for the lakehouse serving layer
#
# Trino provides:
# - Federated query across Bronze/Silver/Gold S3 layers via Glue catalog
# - JDBC/ODBC connectivity for BI tools (Tableau, Power BI)
# - Sub-second query latency on Gold layer aggregates
# - ANSI SQL compatibility for analyst teams migrating from Oracle
#
# Deployment: ECS Fargate (serverless containers) for the Trino cluster
##############################################################################

# ===========================================================================
# ECS Cluster for Trino
# ===========================================================================

resource "aws_ecs_cluster" "trino" {
  name = "${var.name_prefix}-trino"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"

      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.trino.name
      }
    }
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-trino-cluster"
    Service = "trino"
  })
}

resource "aws_ecs_cluster_capacity_providers" "trino" {
  cluster_name = aws_ecs_cluster.trino.name

  capacity_providers = ["FARGATE"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# ===========================================================================
# Trino Coordinator Task Definition
# ===========================================================================

resource "aws_ecs_task_definition" "trino_coordinator" {
  family                   = "${var.name_prefix}-trino-coordinator"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 4096
  memory                   = 16384
  execution_role_arn       = aws_iam_role.trino_execution.arn
  task_role_arn            = aws_iam_role.trino_task.arn

  container_definitions = jsonencode([
    {
      name  = "trino-coordinator"
      image = "trinodb/trino:435"
      essential = true

      portMappings = [
        {
          containerPort = 8443
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "TRINO_NODE_TYPE", value = "coordinator" },
        { name = "TRINO_DISCOVERY_URI", value = "https://localhost:8443" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.trino.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "coordinator"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -fsk https://localhost:8443/v1/info || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-trino-coordinator-td"
    Service = "trino"
  })
}

# ===========================================================================
# Trino Worker Task Definition
# ===========================================================================

resource "aws_ecs_task_definition" "trino_worker" {
  family                   = "${var.name_prefix}-trino-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 4096
  memory                   = 30720
  execution_role_arn       = aws_iam_role.trino_execution.arn
  task_role_arn            = aws_iam_role.trino_task.arn

  container_definitions = jsonencode([
    {
      name  = "trino-worker"
      image = "trinodb/trino:435"
      essential = true

      portMappings = [
        {
          containerPort = 8443
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "TRINO_NODE_TYPE", value = "worker" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.trino.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-trino-worker-td"
    Service = "trino"
  })
}

# ===========================================================================
# Trino ECS Services
# ===========================================================================

resource "aws_ecs_service" "trino_coordinator" {
  name            = "${var.name_prefix}-trino-coordinator"
  cluster         = aws_ecs_cluster.trino.id
  task_definition = aws_ecs_task_definition.trino_coordinator.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.trino_coordinator.arn
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-trino-coordinator-svc"
    Service = "trino"
  })
}

resource "aws_ecs_service" "trino_worker" {
  name            = "${var.name_prefix}-trino-worker"
  cluster         = aws_ecs_cluster.trino.id
  task_definition = aws_ecs_task_definition.trino_worker.arn
  desired_count   = var.trino_node_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-trino-worker-svc"
    Service = "trino"
  })
}

# ===========================================================================
# Service Discovery (for Trino coordinator DNS)
# ===========================================================================

resource "aws_service_discovery_private_dns_namespace" "trino" {
  name        = "trino.${var.name_prefix}.internal"
  description = "Private DNS namespace for Trino service discovery"
  vpc         = var.vpc_id

  tags = var.common_tags
}

resource "aws_service_discovery_service" "trino_coordinator" {
  name = "coordinator"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.trino.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = var.common_tags
}

# ===========================================================================
# IAM Roles for ECS Tasks
# ===========================================================================

resource "aws_iam_role" "trino_execution" {
  name = "${var.name_prefix}-trino-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy_attachment" "trino_execution" {
  role       = aws_iam_role.trino_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "trino_task" {
  name = "${var.name_prefix}-trino-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

resource "aws_iam_role_policy" "trino_task" {
  name = "${var.name_prefix}-trino-task-policy"
  role = aws_iam_role.trino_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::meridian-atlas-*",
          "arn:aws:s3:::meridian-atlas-*/*"
        ]
      },
      {
        Sid    = "GlueCatalogAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition"
        ]
        Resource = ["*"]
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = ["*"]
      }
    ]
  })
}

# ===========================================================================
# CloudWatch Log Group
# ===========================================================================

resource "aws_cloudwatch_log_group" "trino" {
  name              = "/aws/ecs/${var.name_prefix}-trino"
  retention_in_days = 30

  tags = merge(var.common_tags, {
    Name    = "${var.name_prefix}-trino-logs"
    Service = "trino"
  })
}
