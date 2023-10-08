variable "db_name" {
    description = "name of db"
    type = string
}

variable "username" {
    description = "username for db login"
    type = string
}

variable "password" {
    description = "password for db login"
    type = string
}

variable "engine" {
  description = "db engine"
  type        = string
}

variable "instance_class" {
  description = "db instance class"
  default = "db.t3.micro"
  type        = string
}

variable "allocated_storage" {
  description = "allocated storage in GB"
  default = 10
  type        = number
}

variable "skip_final_snapshot" {
  description = "allows tf destroy to remove me"
  default = true
  type        = bool
}

variable "db_subnet_group_name" {
  description = "subnet group name in which to deploy db"
  type        = string
}

variable "vpc_security_group_ids" {
  description = "list of security group ids to apply to db"
  type        = list(string)
}