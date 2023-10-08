variable "vpc_cidr" {
  type        = string
  default     = "10.123.0.0/16"
  description = "cidr block of vpc"
}

variable "my_ip_block" {
  type        = string
  default     = "0.0.0.0/0"
  description = "my ip/32"
}

variable "public_subnet_1_cidr" {
  type        = string
  default     = "10.123.0.0/24"
  description = "public subnet 1"
}

variable "public_subnet_2_cidr" {
  type        = string
  default     = "10.123.1.0/24"
  description = "public subnet 2 cidr"
}

variable "public_subnet_3_cidr" {
  type        = string
  default     = "10.123.2.0/24"
  description = "public subnet 3 cidr"
}
