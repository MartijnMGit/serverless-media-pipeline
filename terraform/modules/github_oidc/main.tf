# Lets GitHub Actions assume an AWS role via short-lived OIDC tokens instead
# of long-lived access keys sitting in GitHub secrets.
#
# thumbprint_list is fetched live rather than hand-copied: AWS technically
# ignores this value for providers backed by a public CA (which GitHub's is),
# but the API still requires a syntactically valid 40-char SHA1 fingerprint,
# and copying it by hand is an easy way to get a silently-truncated string.
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [replace(data.tls_certificate.github.certificates[0].sha1_fingerprint, ":", "")]
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Allow the main-branch deploy workflow and PR-triggered plan/test checks,
    # nothing else (no arbitrary branches/forks).
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main",
        "repo:${var.github_org}/${var.github_repo}:pull_request",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.project}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

# Scoped to the services this stack actually uses. Several AWS APIs
# (list/describe calls) don't support resource-level ARNs, so those stay
# account-wide; everything creatable is scoped to this project's resources.
data "aws_iam_policy_document" "deploy" {
  statement {
    sid = "ProjectResources"
    actions = [
      "s3:*",
      "dynamodb:*",
      "lambda:*",
      "apigateway:*",
      "states:*",
      "sns:*",
      "cloudfront:*",
      "events:*",
      "budgets:*",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "IamForLambdaAndStateMachineRoles"
    actions   = ["iam:*"]
    resources = ["arn:aws:iam::*:role/${var.project}-*", "arn:aws:iam::*:policy/${var.project}-*"]
  }

  statement {
    sid       = "AcmForCloudFrontCert"
    actions   = ["acm:*"]
    resources = ["*"]
  }

  statement {
    sid       = "Route53ForDnsRecords"
    actions   = ["route53:GetHostedZone", "route53:ChangeResourceRecordSets", "route53:ListResourceRecordSets", "route53:GetChange"]
    resources = ["*"]
  }

  statement {
    sid       = "LogsAndMetrics"
    actions   = ["logs:*", "cloudwatch:*"]
    resources = ["*"]
  }

  statement {
    sid       = "TerraformStateBackend"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "${var.project}-github-actions-policy"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.deploy.json
}
