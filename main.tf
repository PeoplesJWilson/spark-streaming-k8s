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
        from_port          = 0
        to_port            = 0
        protocol           = "-1"
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
resource "aws_security_group" "db_sg" {
    name        = "db-sg"
    description = "security group for rds and redis - allows ingress from workers and masters"
    vpc_id      = module.networking.main_vpc_id

    ingress {
        from_port        = 0
        to_port          = 0
        protocol         = "-1"
        security_groups = [aws_security_group.master_sg.id, aws_security_group.worker_sg.id]
    }
    
    egress {
        from_port        = 0
        to_port          = 0
        protocol         = "-1"
        cidr_blocks      = ["0.0.0.0/0"]
        ipv6_cidr_blocks = ["::/0"]
    }
}

# postgres rds and redis elasticache
module "rdsDB" {
  source = "./modules/rds"

  db_name              = local.postgres_db_name
  engine               = "postgres"
  username             = local.postgres_username
  password             = local.postgres_password
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name = module.networking.rds_subnet_group_name
}

resource "aws_elasticache_cluster" "redis_cache" {
  cluster_id           = "airflow-redis"
  engine               = "redis"
  node_type            = "cache.t2.medium"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"

  subnet_group_name = module.networking.cache_subnet_group_name
  security_group_ids = [aws_security_group.db_sg.id]
}

#_________________________________________________________

#           Templating k8s manifests & helm values.yaml

# generate the Helm values.yaml file
data "template_file" "helm_values" {
  template = file("./node-data/master/airflow/values.yaml.tpl")
  vars = {
    twelve_data_key = local.twelve_data_key
    n_samples = local.n_samples
    yaml_symbol_string = local.yaml_symbol_string

    postgres_db_name = local.postgres_db_name
    postgres_username = local.postgres_username
    postgres_password = local.postgres_password
    airflow_username = local.airflow_username
    airflow_password = local.airflow_password
    postgres_endpoint = module.rdsDB.rds_db_endpoint
    redis_endpoint = aws_elasticache_cluster.redis_cache.cache_nodes[0].address
  }
}
# Write the generated values to a file
resource "local_file" "helm_values" {
  filename = "./node-data/master/airflow/values.yaml"
  content  = data.template_file.helm_values.rendered
}
# generate a single worker spark cluster for each symbol
module "spark_templates" {
  source = "./modules/spark-templating"
  for_each = toset(local.spark)

  spark_master_name = "spark-master-${each.value}"
  spark_worker_name = "spark-worker-${each.value}"

  path_to_spark_master = "./node-data/master/spark/spark-master-${each.value}-deployment.yaml"
  path_to_spark_master_service = "./node-data/master/spark/spark-master-${each.value}-service.yaml"
  path_to_spark_worker = "./node-data/master/spark/spark-worker-${each.value}-deployment.yaml"
}
#_________________________________________________________



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
module "masterNodes" {
    source = "./modules/k8s-node"
    for_each = toset(local.master_nodes)
    
    node_name = "master-node-${each.value}"
    bucket_name = module.joinBucket.s3_bucket_name
    join_command_filename = "join-command.sh"

    instance_type = "t2.medium"
    security_group_id = aws_security_group.master_sg.id

    subnet_id = module.networking.public_subnet_1
    instance_profile_name = module.s3Full.instance_profile_name

    path_to_node_data = "node-data/master"
    path_to_bootstrap_template = "node-data/master/bootstrap_template.sh"
    path_to_bootstrap = "node-data/master/bootstrap.sh"

    root_volume_size = 16

    depends_on = [local_file.helm_values, module.spark_templates]

}

# create some worker nodes
module "workerNodes" {
    source = "./modules/k8s-node"
    for_each = toset(local.worker_nodes)

    node_name = "worker-node-${each.value}"

    bucket_name = module.joinBucket.s3_bucket_name
    join_command_filename = "join-command.sh"

    instance_type = "t2.medium"
    security_group_id = aws_security_group.worker_sg.id

    subnet_id = module.networking.public_subnet_1
    instance_profile_name = module.s3Full.instance_profile_name

    path_to_node_data = "node-data/worker"
    path_to_bootstrap_template = "node-data/worker/bootstrap_template.sh"
    path_to_bootstrap = "node-data/worker/bootstrap.sh"

    root_volume_size = 16

    depends_on = [module.masterNodes]

}