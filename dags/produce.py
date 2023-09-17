import datetime
import pendulum
import os
import json
from time import sleep

from airflow.decorators import task,dag
from airflow.operators.dummy_operator import DummyOperator
from airflow import DAG

from kafka import KafkaProducer
from twelvedata import TDClient

# passed to tasks
env_vars = list(os.environ)
SYMBOLS = [os.environ[symbol] for symbol in env_vars if symbol.startswith('SYMBOL')]
TOPICS = [os.environ[topic] for topic in env_vars if topic.startswith('TOPIC')]
N_SAMPLES = int(os.environ["N_SAMPLES"])

# global
API_KEY = os.environ["TWELVE_DATA_KEY"]     # sensitive - comes from .local.env 
KAFKA_SERVER_PORT = os.environ["KAFKA_SERVER_PORT"]
MONGO_SERVER_PORT = os.environ["MONGO_SERVER_PORT"]
MONGO_DBNAME = os.environ["MONGO_DBNAME"]



"""
# dag definition
default_args = {
    'owner': 'PeoplesJWilson',
    'catchup': False,
    'schedule_interval': '25 1 * * *', 
}

dag = DAG(
    'produce_dag',
    start_date=pendulum.datetime(year=2023, month=9, day=15, tz="UTC"),
    default_args=default_args,
    description='This dag fetches minute tick data from SYMBOLS using the twelvedata api, and produces them to various Kafka TOPICS',
)
"""
@dag(
    start_date=pendulum.datetime(year = 2023, month = 9, day =7, tz="UTC"),
    catchup=False,
    schedule='20 23 * * *'
)
def produce_dag():
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
        for i in range(N_SAMPLES):
            print(f"Number {i} out of {N_SAMPLES}")


            # avoid collected duplicates by waiting long enough
            minute = datetime.datetime.now().replace(second=0).replace(microsecond=0)
            while (minute - minute_last) < datetime.timedelta(minutes=1):
                print("Hasn't been 1 minute yet ... waiting ... ")
                sleep(5)
                minute = datetime.datetime.now()

            print("... fetching current minute tick data ...")
            ts = td.time_series(symbol=symbols, interval="1min", outputsize=1)
            json_data = ts.as_json()        # dictionary with keys as symbols, values as ({datetime,open,close,high,low,volume},)
            
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

                print(f"python output:{datum}")
                print("sending to kafka")
                producer.send(topic, value=data)

            # ... after all symbols are sent, wait for next minute ... 
            print("... sleeping ...")
            sleep(20)
            print("... awake ...")



    # dag architecture:      
    start = DummyOperator(task_id="start")
    end = DummyOperator(task_id="end")

    ema_starting_data = warmstart([12,16,30], SYMBOLS, TOPICS)
    produce_to_topics = produce(ema_starting_data, SYMBOLS, TOPICS)

    start >> ema_starting_data >> produce_to_topics >> end

produce_dag()
