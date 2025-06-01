terraform { 
  backend "remote" { 
    organization = "doneztech" 

    workspaces { 
      name = "odoo-infra" 
    } 
  } 
}
provider "aws" {
  region = var.aws_region
}
resource "aws_security_group" "ec2_sg" {
  name = "ec2_sg"
  description = "Allow SSH, HTTP and HTTPS"
  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_instance" "odoo" {
  ami = "ami-084568db4383264d4"
  instance_type = "t3.medium"
  name = var.instance_name
  availability_zone = "ca-central-1a"
  key_name = var.key_pair_name
}
