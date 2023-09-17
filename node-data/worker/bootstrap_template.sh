#!/bin/bash

sleep 60

# S3 bucket and file information
S3_PATH="s3://${S3_BUCKET}/${JOIN_COMMAND_FILE}"

# Function to log errors and exit on failure
check_error() {
  if [ $? -ne 0 ]; then
    local error_message="Error: $1"
    echo "$error_message"
    exit 1
  fi
}


# Install the AWS CLI
sudo apt-get update
sudo apt-get install -y awscli
check_error "Failed to install AWS CLI"

# Update package list and install required packages
sudo apt-get update
sudo apt-get install -y apt-transport-https curl
check_error "Failed to install apt-transport-https and curl"

# Add Kubernetes repository and update package list
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
check_error "Failed to add Kubernetes repository key"
cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
deb https://apt.kubernetes.io/ kubernetes-xenial main
EOF
check_error "Failed to add Kubernetes repository"
sudo apt-get update

# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
check_error "Failed to update /etc/fstab to disable swap"

#       Install Docker and add user to the docker group
sudo apt-get update
sudo apt install docker.io -y
sudo usermod -aG docker ubuntu

# Restart Docker service
sudo systemctl restart docker
sudo systemctl enable docker.service
check_error "Failed to enable Docker service"

# Install Kubernetes components
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
check_error "Failed to install Kubernetes components"

# Start and enable kubelet service
sudo systemctl daemon-reload
sudo systemctl start kubelet
sudo systemctl enable kubelet.service
check_error "Failed to enable kubelet service"


# Download join-command.txt to S3
aws s3 cp "$S3_PATH" "./${JOIN_COMMAND_FILE}"
check_error "Failed to download join-command.txt to S3"

# Join worker to master
chmod +x ./${JOIN_COMMAND_FILE}
./${JOIN_COMMAND_FILE}
check_error "Failed to join worker to master"

echo "Kubernetes setup completed successfully."