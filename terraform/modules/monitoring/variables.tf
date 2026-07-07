variable "project" {
  type = string
}

variable "region" {
  type = string
}

variable "lambda_function_names" {
  type = list(string)
}

variable "state_machine_arn" {
  type = string
}
