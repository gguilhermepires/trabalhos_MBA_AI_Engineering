# N2.3 — alarme sobre a métrica Errors da Lambda (>= 1 erro em 5 min).
# Errors conta só exceções/timeouts da função; um 404 devolvido pelo handler NÃO conta.
resource "aws_cloudwatch_metric_alarm" "lambda_erros" {
  alarm_name          = "${local.nome}-catalogo-erros"
  alarm_description   = "Lambda do catálogo com >= 1 erro em 5 minutos"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.catalogo.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching" # sem tráfego não é erro
}
