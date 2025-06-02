variable "aws_region" {
  description = "AWS region to deploy"
  type = string
  default = "ca-central-1"
}

variable "instance_name" {
  description = "Name of lightsail instance"
  type = string
  default = "odoo_server"
}

variable "ssh_public_key" {
  description = "SSH key pair name for access which is git deply key"
  type = string
  default = "id_rsa"
}
