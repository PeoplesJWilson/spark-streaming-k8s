from airflow.contrib.operators.spark_submit_operator import SparkSubmitOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow import DAG

import pendulum
import os


# topics to stream from --> connection {{spark_conn_name}} already created in setup_dag

spark_conn_name = os.environ["spark_conn_name"]
env_vars = list(os.environ)
TOPICS = [os.environ[topic] for topic in env_vars if topic.startswith('TOPIC')]

scala_dependencies = [depend for depend in env_vars if depend.startswith('scala_dependency')]
scala_dependencies = ",".join(scala_dependencies)   #formatting for SparkSubmitOperator

# Ports --> passed to scala application 
KAFKA_SERVER_PORT = os.environ["KAFKA_SERVER_PORT"]
MONGO_SERVER_PORT = os.environ["MONGO_SERVER_PORT"]     # database stream is read to 
MONGO_DBNAME = os.environ["MONGO_DBNAME"]


# dag definition
default_args = {
    'owner': 'PeoplesJWilson',
    'schedule_interval': '20 1 * * *', 
}

dag = DAG(
    'spark_submit_dag',
    start_date=pendulum.datetime(year=2023, month=9, day=7, tz="UTC"),
    default_args=default_args,
    description='Your DAG description',
    catchup=False
)

# dag architecture 

start = DummyOperator(task_id="start", dag=dag)
end = DummyOperator(task_id="end", dag=dag)

for topic in TOPICS:
    task_id = f"spark_submit_{topic}_job"

    spark_job = SparkSubmitOperator(
        application="/opt/airflow/dags/kafka-streaming_2.12-2.0.jar",
        conf={"spark.yarn.submit.waitAppCompletion": False},
        conn_id=spark_conn_name, 
        task_id=task_id,
        name=task_id,
        packages=scala_dependencies,
        java_class='KafkaStreams',
        application_args=[KAFKA_SERVER_PORT,MONGO_SERVER_PORT,MONGO_DBNAME, topic], 
        dag=dag
        )
    
    start >> spark_job >> end

