#__________________________________________________
/*Defines VPC, 2 private subnets, 1 public subnet*/
resource "aws_vpc" "vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = "us-east-2a"
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private_subnet_1" {
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = var.private_subnet_1_cidr
  availability_zone       = "us-east-2b"
  map_public_ip_on_launch = false
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = var.private_subnet_2_cidr
  availability_zone       = "us-east-2c"
  map_public_ip_on_launch = false
}

resource "aws_db_subnet_group" "private_subnet_group" {
  name       = "private subnet group"
  subnet_ids = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
  
}
#__________________________________________________

# Setup igw, and nat gateway
resource "aws_internet_gateway" "ig" {
  vpc_id = aws_vpc.vpc.id
}

resource "aws_eip" "nat_eip" {
  domain = "vpc"
  depends_on = [aws_internet_gateway.ig]
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet.id
  depends_on    = [aws_internet_gateway.ig]
}
#______________________________________________________

# Configure private routing
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.vpc.id
}

resource "aws_route" "private_nat_gateway" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
}

resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_subnet_2.id
  route_table_id = aws_route_table.private.id
}
#_______________________________________________________

# Configure public routing
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.vpc.id
}

resource "aws_route" "public_internet_gateway" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.ig.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public.id
}
#___________________________________________________________

# Put default security group on VPC
resource "aws_security_group" "default" {
  name        = "vpc-sg"
  description = "Default security group to allow inbound/outbound from the VPC"
  vpc_id      = aws_vpc.vpc.id
  depends_on  = [aws_vpc.vpc]
  ingress {
    from_port = "0"
    to_port   = "0"
    protocol  = "-1"
    self      = "true"
    cidr_blocks = [var.my_ip_block, var.vpc_cidr]
  }
  
  egress {
    from_port = "0"
    to_port   = "0"
    protocol  = "-1"
    self      = "true"
  }
}