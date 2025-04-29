output "odoo_server_ip" {
  value = aws_lightsail_static_ip.odoo_ip.ip_address
}