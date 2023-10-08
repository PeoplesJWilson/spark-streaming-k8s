output "rds_db_endpoint" {
  value = aws_db_instance.rds_db.address
}
# mysql-connector-python uses the address as the endpoint 
# and has a separate port argument which defaults to 3306