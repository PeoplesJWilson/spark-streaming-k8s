data "template_file" "master" {
  template = file("${path.module}/templates/spark-master-deployment.yaml.tpl")
  vars = {
    spark_master_name = var.spark_master_name
  }
}
resource "local_file" "master" {
  filename = var.path_to_spark_master
  content  = data.template_file.master.rendered
}


data "template_file" "master_service" {
  template = file("${path.module}/templates/spark-master-service.yaml.tpl")
  vars = {
    spark_master_name = var.spark_master_name
  }
}

resource "local_file" "master_service" {
  filename = var.path_to_spark_master_service
  content  = data.template_file.master_service.rendered
}

data "template_file" "worker" {
  template = file("${path.module}/templates/spark-worker-deployment.yaml.tpl")
  vars = {
    spark_master_name = var.spark_master_name
    spark_worker_name = var.spark_worker_name
  }
}
resource "local_file" "worker" {
  filename = var.path_to_spark_worker
  content  = data.template_file.worker.rendered
}