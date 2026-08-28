variable "project_name" {
  type    = string
  default = "cloud-cost-monitor"
}

variable "aws_region" {
  type    = string
  default = "ca-central-1"
}

variable "container_image" {
  type        = string
  description = "Published backend container image"
}

variable "monthly_budget" {
  type    = number
  default = 10000
}

variable "alert_email" {
  type        = string
  default     = ""
  description = "Optional SNS email subscription"
}

variable "database_username" {
  type    = string
  default = "finops"
}

variable "database_password" {
  type      = string
  sensitive = true
}

