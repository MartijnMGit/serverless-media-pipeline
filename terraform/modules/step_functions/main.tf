data "aws_iam_policy_document" "sfn_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "state_machine" {
  name               = "${var.project}-state-machine-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume_role.json
}

data "aws_iam_policy_document" "state_machine" {
  statement {
    sid       = "InvokePipelineLambdas"
    actions   = ["lambda:InvokeFunction"]
    resources = [var.process_image_arn, var.analyze_image_arn, var.save_metadata_arn]
  }

  statement {
    sid       = "PublishNotifications"
    actions   = ["sns:Publish"]
    resources = [var.sns_topic_arn]
  }

  statement {
    sid = "WriteExecutionLogs"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "state_machine" {
  name   = "${var.project}-state-machine-policy"
  role   = aws_iam_role.state_machine.id
  policy = data.aws_iam_policy_document.state_machine.json
}

resource "aws_cloudwatch_log_group" "state_machine" {
  name              = "/aws/states/${var.project}"
  retention_in_days = 14
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.project}-pipeline"
  role_arn = aws_iam_role.state_machine.arn

  definition = templatefile("${path.module}/../../../step_functions/pipeline.asl.json.tftpl", {
    process_image_arn = var.process_image_arn
    analyze_image_arn = var.analyze_image_arn
    save_metadata_arn = var.save_metadata_arn
    sns_topic_arn     = var.sns_topic_arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.state_machine.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
}

# S3 -> EventBridge -> Step Functions. No shim Lambda needed: S3 can publish
# object-created events straight onto the default EventBridge bus, and a rule
# starts the state machine execution directly.
resource "aws_s3_bucket_notification" "eventbridge" {
  bucket      = var.media_bucket_id
  eventbridge = true
}

resource "aws_cloudwatch_event_rule" "on_upload" {
  name = "${var.project}-on-upload"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [var.media_bucket_id]
      }
      object = {
        key = [{ prefix = "uploads/" }]
      }
    }
  })
}

data "aws_iam_policy_document" "eventbridge_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbridge_invoke" {
  name               = "${var.project}-eventbridge-invoke-role"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role.json
}

data "aws_iam_policy_document" "eventbridge_invoke" {
  statement {
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.pipeline.arn]
  }
}

resource "aws_iam_role_policy" "eventbridge_invoke" {
  name   = "${var.project}-eventbridge-invoke-policy"
  role   = aws_iam_role.eventbridge_invoke.id
  policy = data.aws_iam_policy_document.eventbridge_invoke.json
}

resource "aws_cloudwatch_event_target" "start_pipeline" {
  rule     = aws_cloudwatch_event_rule.on_upload.name
  arn      = aws_sfn_state_machine.pipeline.arn
  role_arn = aws_iam_role.eventbridge_invoke.arn

  input_transformer {
    input_paths = {
      bucket = "$.detail.bucket.name"
      key    = "$.detail.object.key"
      time   = "$.time"
    }
    input_template = <<EOF
{
  "bucket": <bucket>,
  "key": <key>,
  "uploaded_at": <time>
}
EOF
  }
}
