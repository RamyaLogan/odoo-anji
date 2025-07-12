resource "aws_db_instance" "odoo_rds" {
  identifier              = "odoo-prod-db"
  engine                  = "postgres"
  engine_version          = "14.15"
  instance_class          = "db.t3.micro" # change to t3.small or t3.medium if needed
  allocated_storage       = 20
  storage_type            = "gp2"
  db_name                 = "odoo"
  username                = var.rds_master_username
  password                = var.rds_master_password
  db_subnet_group_name = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids  = [aws_security_group.odoo_rds_sg.id]
  skip_final_snapshot     = true
  publicly_accessible     = false
  multi_az                = false

  tags = {
    Name = "odoo-rds"
  }
  lifecycle {
    prevent_destroy = true
    ignore_changes = [vpc_security_group_ids]
  }
}

resource "aws_security_group" "odoo_rds_sg" {
  name        = "odoo-rds-sg"
  description = "Allow EC2 access to RDS"
  vpc_id = data.aws_vpc.odoo_vpc.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    security_groups = [aws_security_group.ec2_sg.id] # EC2 SG
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  lifecycle {
    prevent_destroy = true
  }
}