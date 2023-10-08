output "rds_subnet_group_name" {
    value = aws_db_subnet_group.rds_subnet_group.name
}

output "cache_subnet_group_name" {
    value = aws_elasticache_subnet_group.cache_subnet_group.name
}

output "public_subnet_1" {
    value = aws_subnet.public_subnet_1.id
}

output "public_subnet_2" {
    value = aws_subnet.public_subnet_2.id
}

output "public_subnet_3" {
    value = aws_subnet.public_subnet_3.id
}

output "main_vpc_id" {
    value = aws_vpc.vpc.id
}