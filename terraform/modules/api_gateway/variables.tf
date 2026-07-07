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
