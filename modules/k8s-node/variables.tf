variable "node_name" {
  description = "Name of node"
  type        = string
}

variable "bucket_name" {
  description = "Name of bucket to upload join command script"
  type        = string
}

variable "join_command_filename" {
  description = "Name of bucket to upload join command script"
  type        = string
}

variable "instance_type" {
  description = "Instance to use for node. E.g. t2.medium"
  type        = string
}

variable "security_group_id" {
  description = "ID of SG to associate with instance"
  type        = string
}

variable "subnet_id" {
  description = "ID of SG to associate with instance"
  type        = string
}

variable "instance_profile_name" {
  description = "Name of iam instance profile to associate"
  type        = string
}

variable "path_to_node_data" {
  description = "path to the node data ... Gives local access to bootstrap scripts and docker-compose to master"
  type        = string
}


variable "path_to_bootstrap_template" {
  description = "path of bootstrap template file"
  type        = string
}

variable "path_to_bootstrap" {
  description = "path of bootstrap file"
  type        = string
}


