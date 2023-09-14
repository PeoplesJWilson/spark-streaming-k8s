TOPICS = ["msft"]  #["aapl", "btc"]
SYMBOLS = ["MSFT"] #["AAPL", "BTC/USD"]
N_SAMPLES = 5 ###395 #number of minutes in a trading day, plus 5 for good measure
spark_conn_name = "spark_default"

# these must match with the dependencies used to build your jar
scala_dependencies = ["org.apache.spark:spark-sql_2.12:3.4.1",
                      "org.mongodb.spark:mongo-spark-connector_2.12:10.2.0",
                      "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1"]



"""
some example symbols: 

"AAPL"
"MSFT"
"GOOGL"
"VFIAX"
"BTC/USD"

"""