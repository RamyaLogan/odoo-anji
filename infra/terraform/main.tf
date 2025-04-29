provider "aws" {
  region = "us-east-1"
}

resource "digitalocean_droplet" "odoo_server" {
  image  = "ubuntu-22-04-x64"
  name   = "odoo-droplet"
  region = "nyc3"
  size   = "s-1vcpu-2gb"
  ssh_keys = [var.ssh_key_id]
}