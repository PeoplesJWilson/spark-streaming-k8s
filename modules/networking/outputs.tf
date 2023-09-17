output "private_subnet_group_name" {
    value = aws_db_subnet_group.private_subnet_group.name
}

output "private_subnet_1_id" {
    value = aws_subnet.private_subnet_1.id
}

output "private_subnet_2_id" {
    value = aws_subnet.private_subnet_2.id
}

output "public_subnet" {
    value = aws_subnet.public_subnet.id
}

output "main_vpc_id" {
    value = aws_vpc.vpc.id
}