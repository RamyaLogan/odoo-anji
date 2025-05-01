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

resource "aws_lightsail_instance" "odoo" {
  name = var.instance_name
  availability_zone = "ca-central-1a"
  blueprint_id = "ubuntu_22_04"
  bundle_id = "medium_2_0"
  key_pair_name = var.key_pair_name
}

resource "aws_lightsail_static_ip" "odoo_ip" {
  name = "odoo-ip"
}

resource "aws_lightsail_static_ip_attachment" "attach_ip" {
  static_ip_name = aws_lightsail_static_ip.odoo_ip.name
  instance_name = aws_lightsail_instance.odoo.name
}
