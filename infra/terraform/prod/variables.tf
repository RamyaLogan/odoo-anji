variable "aws_region" {
  description = "AWS region to deploy"
  type = string
  default = "ap-south-1"
}

variable "instance_name" {
  description = "Name of lightsail instance"
  type = string
  default = "odoo_server"
}

variable "ssh_public_key" {
  description = "SSH key pair name for access which is git deply key"
  type = string
}

variable "rds_master_username" {
  description = "Master username for RDS PostgreSQL"
  type        = string
}

variable "rds_master_password" {
  description = "Master password for RDS PostgreSQL"
  type        = string
  sensitive   = true
}

