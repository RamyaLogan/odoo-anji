output "odoo_public_ip" {
  value = aws_lightsail_static_ip.odoo_ip.ip_address
}