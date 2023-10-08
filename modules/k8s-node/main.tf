data "aws_ami" "ubuntu" {

    most_recent = true

    filter {
        name   = "name"
        values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
    }

    filter {
        name = "virtualization-type"
        values = ["hvm"]
    }

    owners = ["099720109477"]
}

# create user data
data "template_file" "bootstrap_template" {
  template = file(var.path_to_bootstrap_template)

  vars = {
    S3_BUCKET = var.bucket_name
    JOIN_COMMAND_FILE = var.join_command_filename
  }
}
resource "local_file" "bootstrap_file" {
 filename = var.path_to_bootstrap
 content = <<EOT
${data.template_file.bootstrap_template.rendered}
EOT
}

# generate key
resource "tls_private_key" "nodeKey" {
  algorithm = "RSA"
  rsa_bits  = 4096
}
resource "aws_key_pair" "nodeKeyPair" {
  key_name   = "${var.node_name}_key"
  public_key = tls_private_key.nodeKey.public_key_openssh

  provisioner "local-exec" {
    command = "echo '${tls_private_key.nodeKey.private_key_pem}' > ./secrets/keys/${var.node_name}_KP.pem"
  }
}


resource "aws_instance" "node" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = aws_key_pair.nodeKeyPair.key_name

  vpc_security_group_ids = [var.security_group_id]
  subnet_id = var.subnet_id

  iam_instance_profile = var.instance_profile_name

  associate_public_ip_address = true

  user_data = data.template_file.bootstrap_template.rendered

  root_block_device {
    volume_size = var.root_volume_size
  }

  provisioner "file" {
    source      = var.path_to_node_data
    destination = "/home/ubuntu"

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = tls_private_key.nodeKey.private_key_pem
      host        = "${self.public_dns}"
  }
}


}

resource "local_file" "ssh" {
 filename = "./secrets/${var.node_name}-ssh.sh"
 content = <<EOT
chmod 400 ./keys/${var.node_name}_KP.pem
ssh -i "./keys/${var.node_name}_KP.pem" ubuntu@${aws_instance.node.public_dns}
# DNS for port viewing: ${aws_instance.node.public_dns}
EOT
}