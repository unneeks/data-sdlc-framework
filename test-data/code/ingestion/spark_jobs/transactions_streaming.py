"""
Project ATLAS — Transactions Streaming Ingestion
Spark Structured Streaming job that consumes real-time transaction events
from MSK (Kafka) and writes to Iceberg tables with exactly-once semantics.

Source: MSK topic `meridian.core_banking.transactions`
Target: s3://meridian-bank-raw/iceberg/transactions (partitioned by transaction_date)
Checkpoint: s3://meridian-bank-config/checkpoints/transactions_streaming/
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, current_timestamp, lit, to_date, hour,
    when, expr, window
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DecimalType,
    TimestampType, IntegerType, BooleanType
)

KAFKA_BOOTSTRAP = "b-1.meridian-msk.eu-west-1.kafka.amazonaws.com:9092"
KAFKA_TOPIC = "meridian.core_banking.transactions"
ICEBERG_CATALOG = "glue_catalog"
ICEBERG_DB = "raw_banking"
ICEBERG_TABLE = "transactions"
S3_WAREHOUSE = "s3://meridian-bank-raw/iceberg"
CHECKPOINT_PATH = "s3://meridian-bank-config/checkpoints/transactions_streaming/"
DEAD_LETTER_PATH = "s3://meridian-bank-raw/dead_letter/transactions/"

TRANSACTION_SCHEMA = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("account_id", StringType(), False),
    StructField("counterparty_account_id", StringType(), True),
    StructField("transaction_type", StringType(), False),
    StructField("transaction_subtype", StringType(), True),
    StructField("amount", DecimalType(18, 4), False),
    StructField("currency_code", StringType(), False),
    StructField("exchange_rate", DecimalType(12, 6), True),
    StructField("base_currency_amount", DecimalType(18, 4), True),
    StructField("transaction_timestamp", TimestampType(), False),
    StructField("value_date", StringType(), False),
    StructField("posting_date", StringType(), True),
    StructField("channel", StringType(), True),
    StructField("merchant_category_code", StringType(), True),
    StructField("merchant_name", StringType(), True),
    StructField("merchant_country", StringType(), True),
    StructField("reference", StringType(), True),
    StructField("narrative", StringType(), True),
    StructField("is_international", BooleanType(), True),
    StructField("fraud_score", DecimalType(5, 4), True),
    StructField("aml_flag", BooleanType(), True),
    StructField("branch_code", StringType(), True),
    StructField("batch_id", StringType(), True),
])


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("atlas-transactions-streaming")
        .config("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.glue_catalog.warehouse", S3_WAREHOUSE)
        .config("spark.sql.catalog.glue_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog")
        .config("spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_PATH)
        .config("spark.sql.shuffle.partitions", "200")
        .getOrCreate()
    )


def validate_transaction(df):
    """Apply basic data quality rules; route invalid records to dead letter."""
    valid = df.filter(
        col("transaction_id").isNotNull()
        & col("account_id").isNotNull()
        & col("amount").isNotNull()
        & col("transaction_type").isin(
            "DEBIT", "CREDIT", "TRANSFER_OUT", "TRANSFER_IN",
            "PAYMENT", "DIRECT_DEBIT", "STANDING_ORDER", "FX_TRADE",
            "INTEREST", "FEE", "REVERSAL"
        )
        & (col("amount") > 0)
    )

    invalid = df.subtract(valid)
    return valid, invalid


def enrich_transaction(df):
    """Add derived columns for downstream consumption."""
    return (
        df
        .withColumn("transaction_date", to_date(col("transaction_timestamp")))
        .withColumn("transaction_hour", hour(col("transaction_timestamp")))
        .withColumn("is_high_value",
                    when(col("base_currency_amount") > 10000, True).otherwise(False))
        .withColumn("requires_sar",
                    when(
                        (col("aml_flag") == True) | (col("base_currency_amount") > 15000),
                        True
                    ).otherwise(False))
        .withColumn("_ingested_at", current_timestamp())
        .withColumn("_source_system", lit("MSK_CDC"))
        .withColumn("_stream_batch_id", col("batch_id"))
    )


def write_to_iceberg(batch_df, batch_id):
    """Micro-batch writer for foreachBatch sink."""
    target = f"{ICEBERG_CATALOG}.{ICEBERG_DB}.{ICEBERG_TABLE}"

    valid, invalid = validate_transaction(batch_df)

    if invalid.count() > 0:
        (invalid
         .withColumn("_rejection_reason", lit("VALIDATION_FAILED"))
         .withColumn("_rejected_at", current_timestamp())
         .write
         .mode("append")
         .parquet(DEAD_LETTER_PATH))

    if valid.count() > 0:
        enriched = enrich_transaction(valid)
        (enriched
         .writeTo(target)
         .option("fanout-enabled", "true")
         .append())


def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    print(f"[ATLAS] Starting transactions streaming from {KAFKA_TOPIC}")

    raw_stream = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .option("kafka.security.protocol", "SASL_SSL")
        .option("kafka.sasl.mechanism", "AWS_MSK_IAM")
        .option("kafka.sasl.jaas.config",
                "software.amazon.msk.auth.iam.IAMLoginModule required;")
        .option("kafka.sasl.client.callback.handler.class",
                "software.amazon.msk.auth.iam.IAMClientCallbackHandler")
        .option("maxOffsetsPerTrigger", "500000")
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed_stream = (
        raw_stream
        .selectExpr("CAST(key AS STRING) as msg_key", "CAST(value AS STRING) as msg_value")
        .select(from_json(col("msg_value"), TRANSACTION_SCHEMA).alias("data"))
        .select("data.*")
    )

    query = (
        parsed_stream.writeStream
        .foreachBatch(write_to_iceberg)
        .outputMode("append")
        .trigger(processingTime="30 seconds")
        .option("checkpointLocation", CHECKPOINT_PATH)
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
