name := "Kafka Streaming"

version := "2.0"

scalaVersion := "2.12.17"

libraryDependencies += "org.apache.spark" %% "spark-sql" % "3.4.1"
libraryDependencies += "org.mongodb.spark" %% "mongo-spark-connector" % "10.2.0"
libraryDependencies += "org.apache.spark" %% "spark-sql-kafka-0-10" % "3.4.1" % Test


