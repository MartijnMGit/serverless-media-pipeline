output "site_url" {
  value = "https://${var.domain_name}"
}

output "api_endpoint" {
  value = module.api_gateway.api_endpoint
}

output "media_bucket_name" {
  value = module.storage.media_bucket_name
}

output "frontend_bucket_name" {
  value = module.storage.frontend_bucket_name
}

output "cloudfront_distribution_id" {
  value = module.cloudfront.distribution_id
}

output "state_machine_arn" {
  value = module.step_functions.state_machine_arn
}

output "dashboard_name" {
  value = module.monitoring.dashboard_name
}

output "github_actions_role_arn" {
  value = module.github_oidc.role_arn
}
