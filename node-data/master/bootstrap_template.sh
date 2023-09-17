#!/bin/bash

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

#         Install Docker and add user to the docker group
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

# Initialize Kubernetes master node (only on the master)
sudo kubeadm init
check_error "Failed to initialize Kubernetes master node"

# Configure kubeconfig for the current user
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
check_error "Failed to configure kubeconfig"
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Configure kubeconfig for the ubuntu user
mkdir -p /home/ubuntu/.kube
cp -i /etc/kubernetes/admin.conf /home/ubuntu/.kube/config
check_error "Failed to configure kubeconfig for ubuntu user"
chown ubuntu:ubuntu /home/ubuntu/.kube/config

# Deploy a network plugin (e.g., Weave Net)
# kubectl apply -f https://github.com/weaveworks/weave/releases/download/v2.8.1/weave-daemonset-k8s-1.11.yaml
kubectl apply -f "https://github.com/weaveworks/weave/releases/download/v2.8.1/weave-daemonset-k8s-1.11.yaml"
check_error "Failed to deploy network plugin"

# Generate and save join command for worker nodes
kubeadm token create --print-join-command > "temp.sh"
(echo -e '#!/bin/bash\n' && cat "temp.sh") > "${JOIN_COMMAND_FILE}"
chmod +x "${JOIN_COMMAND_FILE}"
check_error "Failed to generate and save join command for worker nodes"

# Upload join-command.txt to S3
aws s3 cp "${JOIN_COMMAND_FILE}" "$S3_PATH"
check_error "Failed to upload join-command.txt to S3"

echo "Kubernetes setup completed successfully."