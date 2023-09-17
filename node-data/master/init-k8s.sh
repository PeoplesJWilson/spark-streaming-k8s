# Don't use a shebang here  !/bin/bash

cd kafka
kubectl apply -f zookeeper-deployment.yaml
kubectl apply -f zookeeper-service.yaml 

echo "... sleeping for two minutes while zookeeper starts up ..."
sleep 120

kubectl apply -f kafka-deployment.yaml
kubectl apply -f kafka-service.yaml
echo "... sleeping for two minutes while bootstrap server kafka starts up ..."
sleep 120 
cd ..


cd mongo
kubectl apply -f . 
cd ..


cd spark
kubectl apply -f spark-deployment.yaml 
kubectl apply -f spark-worker-deployment.yaml 
kubectl apply -f spark-service.yaml
echo "... sleeping for two minutes while the spark master starts up"
sleep 120
cd ..


cd dashboard
kubectl apply -f . -n dashboard
cd ..

kubectl create namespace airflow
cd airflow
helm install airflow-streaming bitnami/airflow -f values.yaml
cd ..

#kubectl port-forward svc/dash 8000:8000
#kubectl port-forward --namespace default svc/airflow-streaming 8080:8080 &
#echo "Airflow URL: http://127.0.0.1:8080" 
