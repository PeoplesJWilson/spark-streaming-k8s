import pendulum
import os
import json
import datetime
from time import sleep

from kubernetes import client, config
from kubernetes.stream import stream

from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic

from twelvedata import TDClient

from airflow.decorators import task,dag
from airflow.operators.dummy_operator import DummyOperator
from airflow import DAG

# passed to tasks
env_vars = list(os.environ)
SYMBOLS = [os.environ[symbol] for symbol in env_vars if symbol.startswith('TOPIC')]
TOPICS = [symbol.lower().replace("/","-") for symbol in SYMBOLS]
N_SAMPLES = int(os.environ["N_SAMPLES"])


# Global variables --> If configured, must be changed in docker-compose
API_KEY = os.environ["TWELVE_DATA_KEY"]     # sensitive - comes from .local.env 
KAFKA_SERVER_PORT = os.environ["KAFKA_SERVER_PORT"]
MONGO_SERVER_PORT = os.environ["MONGO_SERVER_PORT"]
MONGO_DBNAME = os.environ["MONGO_DBNAME"]
scala_dependencies = [os.environ[dependency] for dependency in env_vars if dependency.startswith('scala_dependency')]

now = pendulum.now()

@dag(
    start_date=now,
    catchup=False,
    schedule='25 13 * * 1-5'
)
def streaming_pipeline():
    # tasks
    @task()
    def warmstart(Ns, SYMBOLS, TOPICS, output_num = 2000, production = False):
        producer = KafkaProducer(bootstrap_servers = [KAFKA_SERVER_PORT],
                                value_serializer = lambda x: json.dumps(x).encode('utf-8'),
                                api_version = (0,10,2))
        print("... kafka producer started ...")
    
        td = TDClient(apikey=API_KEY)
        print("... connceted to API ...")
        symbols = ",".join(SYMBOLS)
        max_N = max(Ns)
        # initial warm startup
        ts = td.time_series(symbol=symbols, interval="1min", outputsize=output_num)
        json_data = ts.as_json()
        if len(SYMBOLS) == 1:
            json_data = {SYMBOLS[0]: json_data}
    
        ema_data = dict()
        for i,symbol in enumerate(SYMBOLS):         # data should be sent to topic TOPICS[i]
            topic = TOPICS[i]
    
            data = json_data[symbol]
            data = tuple(reversed(data))
    
            start_date = data[0]["datetime"]       # log warmup date info
            end_date = data[-1]["datetime"]
            print(f"data for {symbol} is from dates {start_date} to {end_date} fetched")
    
            print("warming up EMAs:")
            ema_starts = []
            processed_data = data
            for N in Ns:
                alpha = 2/(N + 1)
                key = f"ema_{N}"
    
                ema = float(data[0]["close"])          # ema starting value
                for index,datum in enumerate(data):
                    ema = alpha*float(datum["close"]) + (1-alpha)*ema           # ema's next value
                    processed_data[index][key] = str(ema)
    
                ema_starts.append((ema, alpha, N))
            
            # compute macd data, estimate support and resistance
            ema_long = f"ema_{max(Ns)}" 
            ema_short = f"ema_{min(Ns)}" 
            alpha = 2/(9 + 1)
            alpha_200 = 2/(200 + 1)
    
            signal = float(processed_data[0][ema_short]) - float(processed_data[0][ema_long])
            ema_200 = float(processed_data[0]["close"])
            for index,datum in enumerate(data):
                macd = float(processed_data[index][ema_short]) - float(processed_data[index][ema_long])
                signal = alpha*float(macd) + (1-alpha)*signal
    
                ema_200 = alpha_200*float(processed_data[index]["close"]) + (1-alpha_200)*ema_200
    
                processed_data[index]["ema_200"] = str(ema_200) 
                processed_data[index]["macd"] = str(macd)
                processed_data[index]["signal"] = str(signal)
                
                processed_data[index]["support"] = '0'
                processed_data[index]["resistance"] = '0'
    
                if index > 7:
                    last_7 = processed_data[index-6:index+1]
                    highs = [datum["high"] for datum in last_7]
                    lows = [datum["low"] for datum in last_7]
    
                    if highs.index(max(highs)) == 4:
                        processed_data[index]["resistance"] =  processed_data[index]["high"]
                    
                    if lows.index(min(lows)) == 4:
                        processed_data[index]["support"] =  processed_data[index]["low"]
                        
            ema_starts.append((ema_200, alpha_200, 200))
            ema_starts.append((signal, alpha, 9))
            
            ema_data[symbol] = ema_starts 
            
            # now all data is processed. send to producer
            for datum in processed_data:
                print(f"Sending {datum} to topic {topic}")
                producer.send(topic, value=datum)
        
        # warmup should only happen at the beginning of day
        if production:
            current = datetime.datetime.now()
            start_time = current.replace(hour=9).replace(minute=30).replace(second=0).replace(microsecond=0)
            print(f"Current time is {current}. Dag should start at {start_time}")
            
            if current > start_time:
                print("Possible error ... dag started after market start ... ")
            
            else:
                print("Waiting until 9:30 to trigger next task")
                while current < start_time:     
                    sleep(20)
                    current = datetime.datetime.now()
        
        return ema_data
    
    @task()
    def produce(ema_data, SYMBOLS, TOPICS):
        producer = KafkaProducer(bootstrap_servers = [KAFKA_SERVER_PORT],
                                value_serializer = lambda x: json.dumps(x).encode('utf-8'),
                                api_version = (0,10,2)) 
        print("... kafka producer started ...")
    
        td = TDClient(apikey=API_KEY)
        print("connceted to API")
    
        symbols = ",".join(SYMBOLS)
    
    
        minute_last = datetime.datetime.now().replace(second=0).replace(microsecond=0) - datetime.timedelta(minutes=1)
        lastSeven = []
        for N_Sample in range(N_SAMPLES):
            print(f"Number {N_Sample} out of {N_SAMPLES}")
    
    
            # avoid collected duplicates by waiting long enough
            minute = datetime.datetime.now().replace(second=0).replace(microsecond=0)
            while (minute - minute_last) < datetime.timedelta(minutes=1):
                print("Hasn't been 1 minute yet ... waiting ... ")
                sleep(5)
                minute = datetime.datetime.now()
    
            print("... fetching current minute tick data ...")
            ts = td.time_series(symbol=symbols, interval="1min", outputsize=1)
            json_data = ts.as_json()        # dictionary with keys as symbols, values as ({datetime,open,close,high,low,volume},)
            print(f"... current data fetched: {json_data}")
            
            # format result in identical way if only using one topic 
            if len(SYMBOLS) == 1:
                json_data = {SYMBOLS[0]: json_data}
    
            minute_last = datetime.datetime.now().replace(second=0).replace(microsecond=0)
            print(f"minute just collected: {minute_last}")
    
            # send data for each symbol to the appropriate topic
            for i,symbol in enumerate(SYMBOLS):
                topic = TOPICS[i]
    
                print("\n")
                print(f"... PROCESSING FOR {topic} ... ")
                print("\n")
                
                data = json_data[symbol]       
                datum = data[0]             # data to process 
                print(f"current data point: {datum}")
    
                ema_starts = ema_data[symbol]   # ema tuple to update ... 
            
                Ns = [N for (ema, alpha, N) in ema_starts]
                Ns = Ns[:-2]
                ema_short = f"ema_{min(Ns)}"
                ema_long = f"ema_{max(Ns)}"
                # compute the next EMA for each N
                new_ema_starts = []
                num_emas = len(ema_starts)
                for index,(ema, alpha, N) in enumerate(ema_starts):
                    if index == (num_emas - 1):
                        key = "signal"
                        macd = float(datum[ema_short]) - float(datum[ema_long])
                        datum["macd"] = macd
                        datum[key] = alpha*float(macd) + (1-alpha)*ema
                    else:
                        key = f"ema_{N}"
                        datum[key] = str(alpha*float(datum["close"]) + (1-alpha)*ema)    # processed data ( with EMAs)
    
                    next_ema = float(datum[key])
                    new_ema_starts.append((next_ema,alpha,N))
    
                ema_data[symbol] = new_ema_starts   # tracking state ... update ema data for next minute
    
                datum["support"] = '0'
                datum["resistance"] = '0'
                if N_Sample < 7:
                    lastSeven.append(datum)
                else:
                    lastSeven.append(datum)
                    lastSeven = lastSeven[-7:]
                    highs = [float(item["high"]) for item in lastSeven]
                    lows = [float(item["low"]) for item in lastSeven]
    
                    if highs.index(max(highs)) == 4:
                        datum["resistance"] =  datum["high"]
                    
                    if lows.index(min(lows)) == 4:
                        datum["support"] = datum["low"]
            
    
                
    
                print(f"python output:{datum}")
                print("sending to kafka")
                producer.send(topic, value=datum)
    
            # ... after all symbols are sent, wait for next minute ... 
            print("... sleeping ...")
            sleep(20)
            print("... awake ...")
    
    
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
    
    @task()
    def spark_submit_command(spark_cluster_number, topic, KAFKA_SERVER_PORT, MONGO_SERVER_PORT, MONGO_DBNAME, scala_dependencies):
        config.load_incluster_config()
        api = client.CoreV1Api()
    
        pod_list = api.list_namespaced_pod(namespace="default")
        worker_name = f"spark-worker-{spark_cluster_number}"
        pod_names = [pod.metadata.name for pod in pod_list.items] 
        matching_workers = [pod_name for pod_name in pod_names if pod_name.startswith(worker_name)]
    
        if len(matching_workers) != 1:
            print(f"Error - Expected pod_names to be of of length 1. Instead, it is {pod_names}")
            return 1
        
        pod_name = matching_workers[0]
        
        master_uri = f"spark://spark-master-{spark_cluster_number}:7077"
        scala_dependencies = ",".join(scala_dependencies) 
        job_name = f"spark_submit_{topic}_job"
    
        cmd_string = f"""spark-submit --master {master_uri} \
    --conf spark.yarn.submit.waitAppCompletion=False \
    --conf spark.yarn.submit.waitAppCompletion=False \
    --packages {scala_dependencies} \
    --name {job_name} \
    --class KafkaStreams /opt/bitnami/spark/jars/kafka-streaming_2.12-2.0.jar \
    {KAFKA_SERVER_PORT} {MONGO_SERVER_PORT} {MONGO_DBNAME} {topic}"""
        cmd_string = cmd_string + " & echo $!"
    
        print(f"spark submit command: {cmd_string}")
    
        resp = stream(api.connect_get_namespaced_pod_exec,
                      name = pod_name,
                      namespace = "default",
                      command=['/bin/sh','-c', cmd_string],
                      stderr=True, stdin=True,
                      stdout=True, tty=False,
                      _preload_content=False)
        
        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                pid = resp.read_stdout()
                print(f"STDOUT: \n{pid}")
                break
            if resp.peek_stderr():
                print(f"STDERR: \n{resp.read_stderr()}")
    
        resp.close()
    
        print(pid)
        return pid
    
    @task()
    def streaming_shutdown(spark_cluster_number, topic, pid):
        config.load_incluster_config()
        api = client.CoreV1Api()
    
        pod_list = api.list_namespaced_pod(namespace="default")
        worker_name = f"spark-worker-{spark_cluster_number}"
        pod_names = [pod.metadata.name for pod in pod_list.items] 
        matching_workers = [pod_name for pod_name in pod_names if pod_name.startswith(worker_name)]
    
        if len(matching_workers) != 1:
            print(f"Error - Expected pod_names to be of of length 1. Instead, it is {pod_names}")
            return 1
        
        pod_name = matching_workers[0]
    
        cmd_str = f"kill -15 {pid}"
    
        resp = stream(api.connect_get_namespaced_pod_exec,
                  name = pod_name,
                  namespace = "default",
                  command=['/bin/sh','-c', cmd_str],
                  stderr=True, stdin=True,
                  stdout=True, tty=False,
                  _preload_content=False)
    
        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                output = resp.read_stdout()
                print(f"STDOUT: \n{output}")
            if resp.peek_stderr():
                print(f"STDERR: \n{resp.read_stderr()}")
    
        resp.close()
        
    
    @task()
    def sleep_task():
        sleep(180)
    
    
    start = DummyOperator(task_id="start")
    end = DummyOperator(task_id="end")

    sleep_1 = sleep_task.override(task_id = "sleep_before_stream")()
    sleep_2 = sleep_task.override(task_id = "sleep_after_stream")()
    
    
    ema_starting_data = warmstart([12,16,30], SYMBOLS, TOPICS)
    produce_to_topics = produce(ema_starting_data, SYMBOLS, TOPICS)

    # dynamically all topics 
    for i,topic in enumerate(TOPICS):
        create_topic = create_kafka_topic.override(task_id = f"create_topic_{topic}")(bootstrap_server=KAFKA_SERVER_PORT, topic_name=topic)
        start_streaming = spark_submit_command.override(task_id = f"start_streaming_from_{topic}")(i, topic, KAFKA_SERVER_PORT, MONGO_SERVER_PORT, MONGO_DBNAME, scala_dependencies)
        stop_streaming = streaming_shutdown.override(task_id = f"stop_streaming_from_{topic}")(i, topic, start_streaming)
        
        start >> create_topic >> start_streaming >> sleep_1 >> ema_starting_data >> produce_to_topics >> sleep_2 >> stop_streaming >> end




streaming_pipeline()




   




