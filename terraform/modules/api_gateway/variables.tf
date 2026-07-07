variable "project" {
  type = string
}

variable "routes" {
  description = "One entry per API route"
  type = list(object({
    route_key            = string # e.g. "POST /uploads"
    lambda_function_name = string
    lambda_invoke_arn    = string
  }))
}

variable "cors_allowed_origins" {
  type    = list(string)
  default = ["*"]
}

variable "throttling_rate_limit" {
  description = "Steady-state requests per second across all routes"
  type        = number
  default     = 10
}

variable "throttling_burst_limit" {
  description = "Maximum concurrent request burst"
  type        = number
  default     = 20
}
