# FALM AWS Infrastructure
# Full production deployment on ECS Fargate

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================================================
# VPC & NETWORKING
# ============================================================================

resource "aws_vpc" "falm" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "falm-vpc"
  }
}

# Public subnets for ALB
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.falm.id
  cidr_block              = "10.0.${count.index}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "falm-public-${count.index + 1}"
  }
}

# Private subnets for ECS tasks
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.falm.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "falm-private-${count.index + 1}"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "falm" {
  vpc_id = aws_vpc.falm.id

  tags = {
    Name = "falm-igw"
  }
}

# NAT Gateway (for private subnets to access internet)
resource "aws_eip" "nat" {
  domain = "vpc"
  depends_on = [aws_internet_gateway.falm]
}

resource "aws_nat_gateway" "falm" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "falm-nat"
  }
}

# Route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.falm.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.falm.id
  }

  tags = {
    Name = "falm-public-rt"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.falm.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.falm.id
  }

  tags = {
    Name = "falm-private-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ============================================================================
# SECURITY GROUPS
# ============================================================================

# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "falm-alb-sg"
  description = "Security group for FALM ALB"
  vpc_id      = aws_vpc.falm.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from internet (redirect to HTTPS)"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "falm-alb-sg"
  }
}

# ECS Tasks Security Group
resource "aws_security_group" "ecs_tasks" {
  name        = "falm-ecs-tasks-sg"
  description = "Security group for FALM ECS tasks"
  vpc_id      = aws_vpc.falm.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "Allow from ALB"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "falm-ecs-tasks-sg"
  }
}

# ============================================================================
# APPLICATION LOAD BALANCER
# ============================================================================

resource "aws_lb" "falm" {
  name               = "falm-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false  # Set to true in production

  tags = {
    Name = "falm-alb"
  }
}

# Target Group
resource "aws_lb_target_group" "falm" {
  name        = "falm-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.falm.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  deregistration_delay = 30

  tags = {
    Name = "falm-tg"
  }
}

# HTTPS Listener (requires ACM certificate)
resource "aws_lb_listener" "https" {
  count             = var.acm_certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.falm.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.falm.arn
  }
}

# HTTP Listener (redirect to HTTPS or forward)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.falm.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = var.acm_certificate_arn != "" ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = var.acm_certificate_arn != "" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    target_group_arn = var.acm_certificate_arn == "" ? aws_lb_target_group.falm.arn : null
  }
}

# ============================================================================
# ECR REPOSITORY
# ============================================================================

resource "aws_ecr_repository" "falm" {
  name                 = "falm"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "falm"
  }
}

# ============================================================================
# ECS CLUSTER
# ============================================================================

resource "aws_ecs_cluster" "falm" {
  name = "falm-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "falm-cluster"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "falm" {
  name              = "/ecs/falm"
  retention_in_days = 7

  tags = {
    Name = "falm-logs"
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution" {
  name = "falm-ecs-task-execution-role"

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
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "falm-ecs-task-role"

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
}

# S3 Access for Task Role
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "falm-ecs-task-s3-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      }
    ]
  })
}

# ECS Task Definition
resource "aws_ecs_task_definition" "falm" {
  family                   = "falm"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "falm"
      image = "${aws_ecr_repository.falm.repository_url}:latest"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "API_HOST"
          value = "0.0.0.0"
        },
        {
          name  = "API_PORT"
          value = "8000"
        },
        {
          name  = "CHROMADB_MODE"
          value = var.chromadb_mode
        },
        {
          name  = "MONGODB_URL"
          value = var.mongodb_url
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "S3_BUCKET"
          value = var.s3_bucket_name
        }
      ]

      secrets = [
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.anthropic_key.arn}"
        },
        {
          name      = "CHROMADB_CLOUD_URL"
          valueFrom = "${aws_secretsmanager_secret.chromadb_url.arn}"
        },
        {
          name      = "CHROMADB_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.chromadb_key.arn}"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.falm.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name = "falm-task"
  }
}

# ECS Service
resource "aws_ecs_service" "falm" {
  name            = "falm-service"
  cluster         = aws_ecs_cluster.falm.id
  task_definition = aws_ecs_task_definition.falm.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.falm.arn
    container_name   = "falm"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name = "falm-service"
  }
}

# Auto Scaling
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.falm.name}/${aws_ecs_service.falm.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu" {
  name               = "falm-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# ============================================================================
# SECRETS MANAGER
# ============================================================================

resource "aws_secretsmanager_secret" "anthropic_key" {
  name = "falm/anthropic_api_key"
}

resource "aws_secretsmanager_secret_version" "anthropic_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_key.id
  secret_string = var.anthropic_api_key
}

resource "aws_secretsmanager_secret" "chromadb_url" {
  name = "falm/chromadb_url"
}

resource "aws_secretsmanager_secret_version" "chromadb_url" {
  secret_id     = aws_secretsmanager_secret.chromadb_url.id
  secret_string = var.chromadb_cloud_url
}

resource "aws_secretsmanager_secret" "chromadb_key" {
  name = "falm/chromadb_api_key"
}

resource "aws_secretsmanager_secret_version" "chromadb_key" {
  secret_id     = aws_secretsmanager_secret.chromadb_key.id
  secret_string = var.chromadb_api_key
}

# ============================================================================
# S3 BUCKET
# ============================================================================

resource "aws_s3_bucket" "falm" {
  bucket = var.s3_bucket_name

  tags = {
    Name = "falm-grants"
  }
}

resource "aws_s3_bucket_versioning" "falm" {
  bucket = aws_s3_bucket.falm.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================================================
# DATA SOURCES
# ============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.falm.dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.falm.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.falm.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.falm.name
}
