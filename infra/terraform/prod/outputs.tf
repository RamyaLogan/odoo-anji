output "odoo_server_ip" {
  value = aws_instance.odoo.public_ip
}
output "public_dns" {
  value = aws_instance.odoo.public_dns
}
output "rds_endpoint" {
  value = aws_db_instance.odoo_rds.endpoint
}