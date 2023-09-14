from twelvedata import TDClient
import datetime
from time import sleep
import os

# passed to tasks
import environment
SYMBOLS = environment.SYMBOLS
TOPICS = environment.TOPICS
N_SAMPLES = environment.N_SAMPLES

# global
API_KEY = os.environ["TWELVE_DATA_KEY"]     # sensitive - comes from .local.env 
KAFKA_SERVER_PORT = "kafka:29092"


def ema_warmstart(Ns, SYMBOLS, TOPICS, production = False):
        #producer = KafkaProducer(bootstrap_servers = [KAFKA_SERVER_PORT],
        #                        value_serializer = lambda x: json.dumps(x).encode('utf-8'),
        #                        api_version = (0,10,2))
        #print("... kafka producer started ...")

        td = TDClient(apikey=API_KEY)
        print("... connceted to API ...")
        symbols = ",".join(SYMBOLS)
        max_N = max(Ns)
        # initial warm startup
        ts = td.time_series(symbol=symbols, interval="1min", outputsize=5*max_N)
        json_data = ts.as_json()

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
            
            ema_data[topic] = ema_starts 
            for datum in processed_data:
                print(f"would send {datum} to {topic}")
                #producer.send(topic, value=datum)
        
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
        print(f"first function output: {ema_data}")
        return ema_data


def produce(ema_data, SYMBOLS, TOPICS):
    #producer = KafkaProducer(bootstrap_servers = [KAFKA_SERVER_PORT],
    #                        value_serializer = lambda x: json.dumps(x).encode('utf-8'),
    #                        api_version = (0,10,2)) 
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

            ema_starts = ema_data[topic]   # ema tuple to update ... 
        

            # compute the next EMA for each N
            new_ema_starts = []
            print(f"Looping through the following list: {ema_starts}")
            print(f"in order to update {datum}")
            for (ema, alpha, N) in ema_starts:
                key = f"ema_{N}"
                datum[key] = str(alpha*float(datum["close"]) + (1-alpha)*ema)    # processed data ( with EMAs)

                next_ema = float(datum[key])
                new_ema_starts.append((next_ema,alpha,N))
        

            ema_data[topic] = new_ema_starts   # tracking state ... update ema data for next minute

            print(f"python output:{datum}")
            print("sending to kafka")
            #producer.send(topic, value=data)

        # ... after all symbols are sent, wait for next minute ... 
        print("... sleeping ...")
        sleep(20)
        print("... awake ...")


ema_starting_data = ema_warmstart([15,20,30], SYMBOLS, TOPICS)
produce_to_topics = produce(ema_starting_data, SYMBOLS, TOPICS)

