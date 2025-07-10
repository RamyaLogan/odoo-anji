output "odoo_server_ip" {
  value = aws_instance.odoo.public_ip
}
output "public_dns" {
  value = aws_instance.odoo.public_dns
}