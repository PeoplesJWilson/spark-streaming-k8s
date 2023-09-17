import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions.{from_json, col, to_timestamp, window, mean, expr}
import org.apache.spark.sql.types.StructType
import org.apache.spark.sql.types.StructField
import org.apache.parquet.format.IntType
import org.apache.spark.sql.types.IntegerType
import org.apache.spark.sql.types.FloatType
import org.apache.spark.sql.types.TimestampType
import org.apache.spark.sql.types.StringType
import com.mongodb.spark._

object KafkaStreams {

  val spark = SparkSession.builder
      .appName("Streaming App")
      .config("spark.master", "local")
      .getOrCreate()

  spark.sparkContext.setLogLevel("ERROR")

  import spark.implicits._

   val schema: StructType = StructType(Seq(
    StructField("datetime", StringType),
    StructField("open", StringType),
    StructField("high", StringType),
    StructField("low", StringType),
    StructField("close", StringType),
    StructField("volume", StringType),
    StructField("ema_12", StringType),
    StructField("ema_16", StringType),
    StructField("ema_30", StringType),
    StructField("ema_200", StringType),
    StructField("macd", StringType),
    StructField("signal", StringType),
    StructField("support", StringType),
    StructField("resistance", StringType)

  ))

  def readFromKafka(kafkaServerPort: String, mongoServerPort: String, mongoDBName: String, kafkaTopic: String) = {
    val lines: DataFrame = spark.readStream
      .format("kafka")
      .option("kafka.bootstrap.servers", kafkaServerPort)
      .option("subscribe", kafkaTopic)
      .load()

    val parsedLines = lines
      .select(
        from_json(col("value").cast("string"), schema).alias("value"))
    
    val typedLines = parsedLines
      .select(
        to_timestamp(col("value.datetime")).alias("datetime"),
        col("value.open").cast("float").alias("open"),
        col("value.high").cast("float").alias("high"),
        col("value.low").cast("float").alias("low"),
        col("value.close").cast("float").alias("close"),
        col("value.volume").cast("int").alias("volume"),
        col("value.ema_12").cast("float").alias("ema_12"),
        col("value.ema_16").cast("float").alias("ema_16"),
        col("value.ema_30").cast("float").alias("ema_30"),
        col("value.ema_200").cast("float").alias("ema_200"),
        col("value.signal").cast("float").alias("signal"),
        col("value.macd").cast("float").alias("macd"),
        col("value.support").cast("float").alias("support"),
        col("value.resistance").cast("float").alias("resistance")
      )
      .withWatermark("datetime", "2 seconds")

      val rollingWindow = typedLines
        .withWatermark("datetime", "2 seconds")
        .groupBy(
          window($"datetime", "20 minutes", "1 minute")
        ).agg(mean("close").alias("sma_20"))


      val joinedDF = typedLines.join(rollingWindow, typedLines("datetime") === rollingWindow("window.end"))

      
      val query = joinedDF.select("datetime","open","high","low","close","volume","ema_12","ema_16","ema_30","ema_200","signal","macd","support","resistance","sma_20") 
      .writeStream
      .format("mongodb")
      .option("checkpointLocation", "/tmp/")
      .option("spark.mongodb.connection.uri", s"mongodb://$mongoServerPort")
      .option("spark.mongodb.database", mongoDBName)
      .option("spark.mongodb.collection", kafkaTopic)
      .outputMode("append")
      .start()
    //  .format("console")
    //  .outputMode("append")
    //  .option("truncate", false)
    //  .start()
      val testQuery = joinedDF.select("datetime","open","high","low","close","volume","ema_12","ema_16","ema_30","ema_200","signal","macd","support","resistance","sma_20") 
        .writeStream
        .format("console")
        .outputMode("append")
        .option("truncate", false)
        .start()

    query.awaitTermination()
    testQuery.awaitTermination()
    
  }


  def main(args: Array[String]) {
      if (args.length != 4) {
      println("Usage: KafkaStreams <kafkaServerPort> <mongoServerPort> <mongoDBName> <kafkaTopic>")
      System.exit(1)
    }

    val kafkaServerPort = args(0)
    val mongoServerPort = args(1)
    val mongoDBName = args(2)
    val kafkaTopic = args(3)
 
    readFromKafka(kafkaServerPort, mongoServerPort, mongoDBName, kafkaTopic)
  
  } 
}