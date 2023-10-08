apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    service: ${spark_master_name}
  name: ${spark_master_name}
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      service: ${spark_master_name}
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        service: ${spark_master_name}
    spec:
      containers:
        - env:
            - name: SPARK_LOCAL_STORAGE_ENCRYPTION_ENABLED
              value: "no"
            - name: SPARK_MODE
              value: master
            - name: SPARK_RPC_AUTHENTICATION_ENABLED
              value: "no"
            - name: SPARK_RPC_ENCRYPTION_ENABLED
              value: "no"
            - name: SPARK_SSL_ENABLED
              value: "no"
            - name: SPARK_USER
              value: spark
          image: peoplesjwilson/streaming-pipeline:spark-master
          name: ${spark_master_name}
          ports:
            - containerPort: 8080
              hostPort: 8000
              protocol: TCP
            - containerPort: 7077
              hostPort: 7077
              protocol: TCP
          resources:
            requests:
              memory: "1024Mi"
              cpu: "1000m"
      restartPolicy: Always
status: {}
