terraform { 
  backend "remote" { 
    organization = "doneztech" 

    workspaces { 
      name = "odoo-mhs-prod" 
    } 
  } 
}
provider "aws" {
  region = var.aws_region
}
resource "aws_key_pair" "deploy_key" {
  key_name = "deploy_key_prod"
  public_key = var.ssh_public_key
}
resource "aws_security_group" "ec2_sg" {
  name = "prod_ec2_sg"
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
  ami = "ami-02521d90e7410d9f0"
  instance_type = "t3.small"
  availability_zone = "ap-south-1a"
  key_name = aws_key_pair.deploy_key.key_name
  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    delete_on_termination = false
  }
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  tags = {
    name = "odoo-prod-ec2"
  }
}
