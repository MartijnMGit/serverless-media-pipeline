variable "project" {
  type = string
}

variable "limit_usd" {
  type = number
}

variable "notification_email" {
  type = string
}

variable "breaker_role_names" {
  description = "Lambda execution role names the circuit breaker denies when the budget is breached"
  type        = list(string)
}
