locals {
  lambda_widgets = [
    for i, name in var.lambda_function_names : {
      type   = "metric"
      x      = (i % 2) * 12
      y      = floor(i / 2) * 6
      width  = 12
      height = 6
      properties = {
        title  = name
        region = var.region
        metrics = [
          ["AWS/Lambda", "Invocations", "FunctionName", name, { stat = "Sum" }],
          ["AWS/Lambda", "Errors", "FunctionName", name, { stat = "Sum" }],
          ["AWS/Lambda", "Duration", "FunctionName", name, { stat = "Average" }],
        ]
        period = 300
        view   = "timeSeries"
      }
    }
  ]

  state_machine_widget = {
    type   = "metric"
    x      = 0
    y      = ceil(length(var.lambda_function_names) / 2) * 6
    width  = 24
    height = 6
    properties = {
      title  = "Pipeline executions"
      region = var.region
      metrics = [
        ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", var.state_machine_arn, { stat = "Sum" }],
        ["AWS/States", "ExecutionsFailed", "StateMachineArn", var.state_machine_arn, { stat = "Sum" }],
      ]
      period = 300
      view   = "timeSeries"
    }
  }
}

resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = "${var.project}-overview"
  dashboard_body = jsonencode({
    widgets = concat(local.lambda_widgets, [local.state_machine_widget])
  })
}
