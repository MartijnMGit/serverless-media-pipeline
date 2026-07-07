resource "aws_budgets_budget" "monthly" {
  name         = "${var.project}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [format("user:Project$%s", var.project)]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.notification_email]
  }
}

# --- Circuit breaker ---
# Budget notifications only email; they never stop spend. This Budgets Action
# is the closest AWS gets to a hard cap: at 100% of the budget it attaches a
# deny-all policy to every pipeline Lambda role, so the next invocation of
# any function fails instantly and cost accumulation stops. Recovery is
# manual and deliberate: detach the policy in the IAM console after
# investigating what burned the budget.

data "aws_iam_policy_document" "deny_all" {
  statement {
    sid       = "CircuitBreakerDenyAll"
    effect    = "Deny"
    actions   = ["*"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "circuit_breaker" {
  name   = "${var.project}-circuit-breaker"
  policy = data.aws_iam_policy_document.deny_all.json
}

data "aws_iam_policy_document" "budgets_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "budget_action" {
  name               = "${var.project}-budget-action"
  assume_role_policy = data.aws_iam_policy_document.budgets_assume_role.json
}

data "aws_iam_policy_document" "budget_action" {
  statement {
    sid     = "AttachBreakerPolicy"
    actions = ["iam:AttachRolePolicy", "iam:DetachRolePolicy"]
    resources = [
      for name in var.breaker_role_names : "arn:aws:iam::*:role/${name}"
    ]
  }
}

resource "aws_iam_role_policy" "budget_action" {
  name   = "${var.project}-budget-action-policy"
  role   = aws_iam_role.budget_action.id
  policy = data.aws_iam_policy_document.budget_action.json
}

resource "aws_budgets_budget_action" "circuit_breaker" {
  budget_name        = aws_budgets_budget.monthly.name
  action_type        = "APPLY_IAM_POLICY"
  approval_model     = "AUTOMATIC"
  notification_type  = "ACTUAL"
  execution_role_arn = aws_iam_role.budget_action.arn

  action_threshold {
    action_threshold_type  = "PERCENTAGE"
    action_threshold_value = 100
  }

  definition {
    iam_action_definition {
      policy_arn = aws_iam_policy.circuit_breaker.arn
      roles      = var.breaker_role_names
    }
  }

  subscriber {
    address           = var.notification_email
    subscription_type = "EMAIL"
  }
}
