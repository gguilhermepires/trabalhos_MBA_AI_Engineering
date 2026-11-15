# N3.4 — Fargate em produção: job agendado, sizing, segredo e auto scaling.
# Complementa lab/terraform/containers.tf (usa aws_ecs_cluster.qc, aws_security_group.api,
# aws_ecs_task_definition.produtos_api, data.aws_iam_role.lab e data.aws_subnets.padrao).

# (a) Job batch: tarefa avulsa disparada por agenda (sem serviço: roda, termina e para de cobrar)
resource "aws_scheduler_schedule" "job_recomendacoes" {
  name                = "${local.nome}-job-recomendacoes"
  schedule_expression = "cron(0 3 * * ? *)"        # 03:00 UTC, todo dia
  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_ecs_cluster.qc.arn
    role_arn = data.aws_iam_role.lab.arn           # em produção: role própria do Scheduler (ecs:RunTask + iam:PassRole)
    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.produtos_api.arn
      launch_type         = "FARGATE"
      task_count          = 1
      network_configuration {
        subnets          = data.aws_subnets.padrao.ids
        security_groups  = [aws_security_group.api.id]
        assign_public_ip = true
      }
    }
    input = jsonencode({
      containerOverrides = [{ name = "produtos-api", command = ["python", "-c", "print('recalcular recomendações')"] }]
    })
  }
}

# (b) Variante com 1 vCPU / 2 GB (a base do lab é 0,25 vCPU / 0,5 GB)
resource "aws_ecs_task_definition" "produtos_api_grande" {
  family                   = "${local.nome}-produtos-api-grande"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = data.aws_iam_role.lab.arn
  task_role_arn            = data.aws_iam_role.lab.arn
  container_definitions    = aws_ecs_task_definition.produtos_api.container_definitions
}

# (c) Segredo injetado pelo ECS (aparece só o ARN na task definition; o valor nunca)
resource "aws_secretsmanager_secret" "chave" {
  name = "qc-aula03/chave-teste"
}
# No container_definitions, em vez de "environment":
#   secrets = [{ name = "CHAVE_VIA_SECRETS", valueFrom = aws_secretsmanager_secret.chave.arn }]
# A execution role precisa de secretsmanager:GetSecretValue nesse ARN.

# (d) Auto scaling por CPU (target tracking 60%)
resource "aws_appautoscaling_target" "api" {
  max_capacity       = 4
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.qc.name}/produtos-api"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${local.nome}-api-cpu60"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 60
    predefined_metric_specification { predefined_metric_type = "ECSServiceAverageCPUUtilization" }
    scale_out_cooldown = 60
    scale_in_cooldown  = 120
  }
}
