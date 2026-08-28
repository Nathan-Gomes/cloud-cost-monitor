terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_vpc" "default" {
  default = true
}
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"
}
resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_security_group" "database" {
  name   = "${var.project_name}-database"
  vpc_id = data.aws_vpc.default.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "collector" {
  name   = "${var.project_name}-collector"
  vpc_id = data.aws_vpc.default.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "database_from_collector" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.database.id
  source_security_group_id = aws_security_group.collector.id
}

resource "aws_db_subnet_group" "main" {
  name       = var.project_name
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "postgres" {
  identifier             = var.project_name
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  db_name                = "finops"
  username               = var.database_username
  password               = var.database_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false
}

resource "aws_secretsmanager_secret" "database" {
  name = "${var.project_name}/database-url"
}
resource "aws_secretsmanager_secret_version" "database" {
  secret_id     = aws_secretsmanager_secret.database.id
  secret_string = "postgresql://${var.database_username}:${urlencode(var.database_password)}@${aws_db_instance.postgres.endpoint}/finops"
}

resource "aws_ecs_cluster" "main" {
  name = var.project_name
}
resource "aws_cloudwatch_log_group" "collector" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14
}

resource "aws_iam_role" "task_execution" {
  name = "${var.project_name}-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  role = aws_iam_role.task_execution.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.database.arn
  }] })
}

resource "aws_iam_role" "collector" {
  name = "${var.project_name}-collector"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}

resource "aws_iam_role_policy" "collector" {
  role = aws_iam_role.collector.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ce:GetCostAndUsage"], Resource = "*" },
      { Effect = "Allow", Action = ["ec2:DescribeInstances", "ec2:DescribeVolumes", "ec2:DescribeSnapshots", "rds:DescribeDBInstances", "cloudwatch:GetMetricStatistics", "cloudwatch:GetMetricData"], Resource = "*" },
      { Effect = "Allow", Action = ["sns:Publish"], Resource = aws_sns_topic.alerts.arn }
    ]
  })
}

resource "aws_ecs_task_definition" "collector" {
  family                   = var.project_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.collector.arn
  container_definitions = jsonencode([{
    name = "collector", image = var.container_image, essential = true,
    command = ["python", "-m", "app.collector_job"],
    environment = [
      { name = "APP_MODE", value = "aws" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "MONTHLY_BUDGET", value = tostring(var.monthly_budget) },
      { name = "SNS_TOPIC_ARN", value = aws_sns_topic.alerts.arn }
    ],
    secrets = [{ name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database.arn }],
    logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.collector.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "collector" } }
  }])
}

resource "aws_iam_role" "scheduler" {
  name = "${var.project_name}-scheduler"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "events.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "scheduler" {
  role = aws_iam_role.scheduler.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecs:RunTask"], Resource = aws_ecs_task_definition.collector.arn },
    { Effect = "Allow", Action = ["iam:PassRole"], Resource = [aws_iam_role.collector.arn, aws_iam_role.task_execution.arn] }
  ] })
}
resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${var.project_name}-daily"
  schedule_expression = "cron(0 6 * * ? *)"
}
resource "aws_cloudwatch_event_target" "collector" {
  rule     = aws_cloudwatch_event_rule.daily.name
  arn      = aws_ecs_cluster.main.arn
  role_arn = aws_iam_role.scheduler.arn
  ecs_target {
    task_definition_arn = aws_ecs_task_definition.collector.arn
    launch_type         = "FARGATE"
    network_configuration {
      subnets          = data.aws_subnets.default.ids
      security_groups  = [aws_security_group.collector.id]
      assign_public_ip = true
    }
  }
}
