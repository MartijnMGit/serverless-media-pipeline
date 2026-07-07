variable "project" {
  type = string
}

variable "domain_name" {
  type = string
}

variable "root_domain_zone_id" {
  type = string
}

variable "frontend_bucket_id" {
  type = string
}

variable "frontend_bucket_arn" {
  type = string
}

variable "frontend_bucket_regional_domain_name" {
  type = string
}

variable "media_bucket_id" {
  type = string
}

variable "media_bucket_arn" {
  type = string
}

variable "media_bucket_regional_domain_name" {
  type = string
}

variable "api_domain_name" {
  description = "API Gateway's execute-api domain name (no https://, no path)"
  type        = string
}
