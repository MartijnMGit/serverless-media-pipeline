variable "function_name" {
  type = string
}

variable "source_dir" {
  description = "Path to the Lambda's source directory, zipped automatically"
  type        = string
}

variable "handler" {
  type    = string
  default = "handler.lambda_handler"
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "timeout" {
  type    = number
  default = 10
}

variable "memory_size" {
  type    = number
  default = 128
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "layers" {
  type    = list(string)
  default = []
}

# Extra IAM policy statements this function needs beyond the basic
# CloudWatch Logs permissions every function gets automatically.
variable "policy_statements" {
  type = list(object({
    sid       = string
    actions   = list(string)
    resources = list(string)
  }))
  default = []
}

variable "log_retention_days" {
  type    = number
  default = 14
}
