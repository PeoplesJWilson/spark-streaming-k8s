apiVersion: v1
kind: Service
metadata:
  labels:
    service: ${spark_master_name}
  name: ${spark_master_name}
  namespace: default
spec:
  ports:
    - name: "8000"
      port: 8000
      targetPort: 8080
    - name: "7077"
      port: 7077
      targetPort: 7077
  selector:
    service: ${spark_master_name}
status:
  loadBalancer: {}
