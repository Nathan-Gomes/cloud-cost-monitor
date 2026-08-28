output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}

output "collector_task_definition" {
  value = aws_ecs_task_definition.collector.arn
}

output "database_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}
