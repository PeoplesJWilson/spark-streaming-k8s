import pendulum
import os
import environment

from airflow.decorators import task
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from kafka.admin import KafkaAdminClient, NewTopic
from airflow import DAG
import sys

sys.path.append("/opt/bitnami/airflow/dags/git_streaming-pipeline-dags/dags")

# User configured variables from environment.py
TOPICS = environment.TOPICS
spark_conn_name = environment.spark_conn_name

# Global variables --> If configured, must be changed in docker-compose
KAFKA_SERVER_PORT = os.environ["KAFKA_SERVER_PORT"]
SPARK_MASTER_SERVER_PORT = os.environ["SPARK_MASTER_SERVER_PORT"]


# dag definition
default_args = {
    'owner': 'PeoplesJWilson',
    'catchup': False,
    'schedule_interval': '10 1 * * *', 
}

dag = DAG(
    'setup_dag',
    start_date=pendulum.datetime(year=2023, month=9, day=7, tz="UTC"),
    default_args=default_args,
    description='This dag creates kafka topics, and initializes a connection to the spark master',
)

# tasks
@task()
def create_spark_connection_cmd_str(conn_name, host):
    return f"""
        airflow connections get --conn_id {conn_name} >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            airflow connections add '{conn_name}' --conn-json '{{
                "conn_type": "Spark",
                "host": "{host}",
                "extra": {{
                    "deploy_mode": "cluster",
                    "spark_home": "/opt/bitnami/spark",
                    "spark_binary": "spark-submit"
                }}
            }}'
            echo "Spark connection created."
        else
            echo "Spark connection already exists."
        fi
        """

@task()
def create_kafka_topic(bootstrap_server, topic_name, num_partitions=1, replication_factor=1):
    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_server)

    # Check if the topic already exists
    topic_exists = topic_name in admin_client.list_topics()
    if topic_exists:
        print(f"Topic '{topic_name}' already exists.")
    else:
        # Create a new topic
        new_topic = NewTopic(name=topic_name, num_partitions=num_partitions, replication_factor=replication_factor)
        admin_client.create_topics(new_topics=[new_topic])
        print(f"Topic '{topic_name}' has been created.")

start = DummyOperator(task_id="start", dag=dag)
end = DummyOperator(task_id="end", dag=dag)

# dynamically all topics 
for i,topic in enumerate(TOPICS):
    create_topic = create_kafka_topic.override(task_id = f"create_topic_{topic}")(bootstrap_server=KAFKA_SERVER_PORT, topic_name=topic)
    start >> create_topic >> end


# create connection to spark master
spark_uri = f"spark://{SPARK_MASTER_SERVER_PORT}"
spark_cmd_str = create_spark_connection_cmd_str(spark_conn_name, spark_uri)

create_spark_connection_task = BashOperator(
    task_id='create_spark_connection_task',
    bash_command=spark_cmd_str,
    dag=dag,
)

start >> spark_cmd_str >> create_spark_connection_task >> end


   





