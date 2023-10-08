# Don't use a shebang here  !/bin/bash
kubectl apply -f rbac.yaml

cd kafka
kubectl apply -f zookeeper-deployment.yaml
kubectl apply -f zookeeper-service.yaml 
kubectl rollout status deployment/zookeeper

kubectl apply -f broker-deployment.yaml
kubectl apply -f broker-service.yaml
kubectl rollout status deployment/broker
cd ..


cd mongo
kubectl apply -f .
kubectl rollout status deployment/mongo 
cd ..


cd spark
kubectl apply -f .
kubectl rollout status deployment/spark-master-0
cd ..


sleep 10

cd airflow
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install airflow-streaming bitnami/airflow -f values.yaml
cd ..

kubectl rollout status deployment/airflow-streaming-scheduler
kubectl rollout status deployment/airflow-streaming-web

kubectl port-forward --namespace default --address 0.0.0.0 svc/airflow-streaming 8080:8080 &
# kubectl port-forward --address 0.0.0.0 svc/dash 8050:8050 &

