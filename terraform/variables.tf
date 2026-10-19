variable "region" {
  description = "AWS region (ap-south-1 = Mumbai)"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 size. t3.small (2 GB RAM) is the minimum that runs the full stack comfortably."
  type        = string
  default     = "t3.small"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair"
  type        = string
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR form, e.g. 203.0.113.5/32"
  type        = string
}

variable "budget_email" {
  description = "Optional: email for a monthly cost alert (budget 10 USD). Leave empty to skip."
  type        = string
  default     = ""
}
