output "odoo_server_ip" {
  value = aws_instance.odoo.public_ip
}
output "public_dns" {
  value = aws_instance.odoo.public_dns
}
output "rds_endpoint" {
  value = aws_db_instance.odoo_rds.endpoint

output "rds_username" {
  value = var.rds_master_username
}
output "rds_password" {
  value     = var.rds_master_password
  sensitive = true
}
output "rds_db_name" {
  value = aws_db_instance.odoo_rds.db_name
}