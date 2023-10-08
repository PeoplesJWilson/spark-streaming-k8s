apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${spark_worker_name}
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      service: ${spark_worker_name}
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        service: ${spark_worker_name}
    spec:
      containers:
        - env:
            - name: SPARK_LOCAL_STORAGE_ENCRYPTION_ENABLED
              value: "no"
            - name: SPARK_MASTER_URL
              value: spark://${spark_master_name}:7077
            - name: SPARK_MODE
              value: worker
            - name: SPARK_RPC_AUTHENTICATION_ENABLED
              value: "no"
            - name: SPARK_RPC_ENCRYPTION_ENABLED
              value: "no"
            - name: SPARK_SSL_ENABLED
              value: "no"
            - name: SPARK_USER
              value: spark
            - name: SPARK_WORKER_CORES
              value: "1"
            - name: SPARK_WORKER_MEMORY
              value: 1G
          image: peoplesjwilson/streaming-pipeline:spark-worker
          name: ${spark_master_name}
          resources:
            requests:
              memory: "1024Mi"
              cpu: "1000m"
      restartPolicy: Always
status: {}
