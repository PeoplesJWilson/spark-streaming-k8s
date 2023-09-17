# creates vpc, 2 private subnets, 1 public subnet, nat gateway, igw, some routes, and vpc-sg
module "networking" {
    source = "./modules/networking"
}

# bucket to hold master node's join command
module "joinBucket" {
    source = "./modules/s3"
    s3_bucket_name = local.join_bucket_name
}


# security groups
resource "aws_security_group" "master_sg" {
    name        = "masterNodeSecurityGroup"
    description = "security group for master node"
    vpc_id      = module.networking.main_vpc_id

    ingress {
        from_port          = 22
        to_port            = 22
        protocol           = "tcp"
        cidr_blocks        = ["0.0.0.0/0"]
    }
    egress {
        from_port        = 0
        to_port          = 0
        protocol         = "-1"
        cidr_blocks      = ["0.0.0.0/0"]
        ipv6_cidr_blocks = ["::/0"]
    }
}
resource "aws_security_group" "worker_sg" {
    name        = "workerNodeSecurityGroup"
    description = "security group for worker nodes - allows ingress from master node"
    vpc_id      = module.networking.main_vpc_id

    ingress {
        from_port        = 0
        to_port          = 0
        protocol         = "-1"
        security_groups = [aws_security_group.master_sg.id]
    }

    ingress {
        from_port          = 22
        to_port            = 22
        protocol           = "tcp"
        cidr_blocks        = ["0.0.0.0/0"]
    }
    
    egress {
        from_port        = 0
        to_port          = 0
        protocol         = "-1"
        cidr_blocks      = ["0.0.0.0/0"]
        ipv6_cidr_blocks = ["::/0"]
    }
}
resource "aws_security_group_rule" "master_allow_worker" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  source_security_group_id = aws_security_group.worker_sg.id
  security_group_id = aws_security_group.master_sg.id
}


# IAM Role 
module "s3Full" {
    source = "./modules/iam"

    iam_policy_name = local.s3_full_policy_name
    iam_policy_path = local.s3_full_policy_path
    iam_role_name   = local.s3_full_role_name

    iam_role_path   = local.iam_role_path

    iam_instance_profile_name = "node-profile"
}


# create a master node
module "masterNode" {
    source = "./modules/k8s-node"

    node_name = "master-node-1"
    bucket_name = module.joinBucket.s3_bucket_name
    join_command_filename = "join-command.sh"

    instance_type = "t2.medium"
    security_group_id = aws_security_group.master_sg.id

    subnet_id = module.networking.public_subnet
    instance_profile_name = module.s3Full.instance_profile_name

    path_to_node_data = "node-data/master"
    path_to_bootstrap_template = "node-data/master/bootstrap_template.sh"
    path_to_bootstrap = "node-data/master/bootstrap.sh"

}

# create two worker nodes
module "workerNodeOne" {
    source = "./modules/k8s-node"

    node_name = "worker-node-1"
    bucket_name = module.joinBucket.s3_bucket_name
    join_command_filename = "join-command.sh"

    instance_type = "t2.medium"
    security_group_id = aws_security_group.worker_sg.id

    subnet_id = module.networking.public_subnet
    instance_profile_name = module.s3Full.instance_profile_name

    path_to_node_data = "node-data/worker"
    path_to_bootstrap_template = "node-data/worker/bootstrap_template.sh"
    path_to_bootstrap = "node-data/worker/bootstrap.sh"

    depends_on = [module.masterNode]

}
module "workerNodeTwo" {
    source = "./modules/k8s-node"

    node_name = "worker-node-2"
    bucket_name = module.joinBucket.s3_bucket_name
    join_command_filename = "join-command.sh"

    instance_type = "t2.medium"
    security_group_id = aws_security_group.worker_sg.id

    subnet_id = module.networking.public_subnet
    instance_profile_name = module.s3Full.instance_profile_name

    path_to_node_data = "node-data/worker"
    path_to_bootstrap_template = "node-data/worker/bootstrap_template.sh"
    path_to_bootstrap = "node-data/worker/bootstrap.sh"

    depends_on = [module.masterNode]

}
module "workerNodeThree" {
    source = "./modules/k8s-node"

    node_name = "worker-node-3"
    bucket_name = module.joinBucket.s3_bucket_name
    join_command_filename = "join-command.sh"

    instance_type = "t2.medium"
    security_group_id = aws_security_group.worker_sg.id

    subnet_id = module.networking.public_subnet
    instance_profile_name = module.s3Full.instance_profile_name

    path_to_node_data = "node-data/worker"
    path_to_bootstrap_template = "node-data/worker/bootstrap_template.sh"
    path_to_bootstrap = "node-data/worker/bootstrap.sh"

    depends_on = [module.masterNode]

}


module "workerNodeFour" {
    source = "./modules/k8s-node"

    node_name = "worker-node-4"
    bucket_name = module.joinBucket.s3_bucket_name
    join_command_filename = "join-command.sh"

    instance_type = "t2.micro"
    security_group_id = aws_security_group.worker_sg.id

    subnet_id = module.networking.public_subnet
    instance_profile_name = module.s3Full.instance_profile_name

    path_to_node_data = "node-data/worker"
    path_to_bootstrap_template = "node-data/worker/bootstrap_template.sh"
    path_to_bootstrap = "node-data/worker/bootstrap.sh"

    depends_on = [module.masterNode]

}
module "workerNodeFive" {
    source = "./modules/k8s-node"

    node_name = "worker-node-5"
    bucket_name = module.joinBucket.s3_bucket_name
    join_command_filename = "join-command.sh"

    instance_type = "t2.micro"
    security_group_id = aws_security_group.worker_sg.id

    subnet_id = module.networking.public_subnet
    instance_profile_name = module.s3Full.instance_profile_name

    path_to_node_data = "node-data/worker"
    path_to_bootstrap_template = "node-data/worker/bootstrap_template.sh"
    path_to_bootstrap = "node-data/worker/bootstrap.sh"

    depends_on = [module.masterNode]

}