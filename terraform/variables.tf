variable "region" {
  description = "Primary AWS region for all resources except the CloudFront ACM cert"
  type        = string
  default     = "eu-west-3"
}

variable "project" {
  description = "Project name, used to prefix resource names"
  type        = string
  default     = "serverless-media-pipeline"
}

variable "domain_name" {
  description = "Subdomain the frontend will be served on"
  type        = string
  default     = "media.martinscloud.be"
}

variable "root_domain_zone_id" {
  description = "Route53 hosted zone ID for martinscloud.be"
  type        = string
  default     = "Z06540953NZ30UV4C3Z9U"
}

variable "notification_email" {
  description = "Email address that receives SNS notifications when an upload finishes processing"
  type        = string
}

variable "budget_limit_usd" {
  description = "Monthly budget alert threshold in USD"
  type        = number
  default     = 5
}

variable "upload_retention_days" {
  description = "Days before uploaded/processed objects are automatically deleted"
  type        = number
  default     = 30
}

variable "github_org" {
  description = "GitHub org/user that owns the repo, for the OIDC trust policy"
  type        = string
  default     = "MartijnMGit"
}

variable "github_repo" {
  description = "GitHub repo name, for the OIDC trust policy"
  type        = string
  default     = "serverless-media-pipeline"
}
