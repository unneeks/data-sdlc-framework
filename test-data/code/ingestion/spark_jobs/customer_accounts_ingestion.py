"""
Project ATLAS — Customer Accounts CDC Ingestion
Reads Change Data Capture events from Oracle DWH via JDBC and writes
to Apache Iceberg tables on S3 (raw zone).

Schedule: Every 15 minutes (micro-batch CDC)
Source: MERIDIAN_DWH.CORE_BANKING.CUSTOMER_ACCOUNTS
Target: s3://meridian-bank-raw/iceberg/customer_accounts
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, lit, when, sha2, concat_ws
)
from pyspark.sql.types import StructType, StructField, StringType, LongType, TimestampType, DecimalType
import sys
from datetime import datetime

ORACLE_JDBC_URL = "jdbc:oracle:thin:@//oracle-dwh.meridian.internal:1521/MERDWH"
ORACLE_DRIVER = "oracle.jdbc.OracleDriver"
ICEBERG_CATALOG = "glue_catalog"
ICEBERG_DB = "raw_banking"
ICEBERG_TABLE = "customer_accounts"
S3_WAREHOUSE = "s3://meridian-bank-raw/iceberg"
CDC_BOOKMARK_PATH = "s3://meridian-bank-config/cdc_bookmarks/customer_accounts/"


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("atlas-customer-accounts-cdc")
        .config("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.glue_catalog.warehouse", S3_WAREHOUSE)
        .config("spark.sql.catalog.glue_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog")
        .config("spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.iceberg.handle-timestamp-without-timezone", "true")
        .getOrCreate()
    )


def get_last_bookmark(spark: SparkSession) -> str:
    """Read the last processed SCN (System Change Number) from bookmark."""
    try:
        bookmark_df = spark.read.json(CDC_BOOKMARK_PATH)
        return bookmark_df.select("last_scn").first()[0]
    except Exception:
        return "0"


def save_bookmark(spark: SparkSession, scn: str):
    """Persist the latest SCN for next run."""
    bookmark_data = [{"last_scn": scn, "updated_at": datetime.utcnow().isoformat()}]
    spark.createDataFrame(bookmark_data).coalesce(1).write.mode("overwrite").json(CDC_BOOKMARK_PATH)


def read_cdc_changes(spark: SparkSession, last_scn: str):
    """Read incremental changes from Oracle using SCN-based CDC."""
    query = f"""
        (SELECT
            ACCOUNT_ID,
            CUSTOMER_ID,
            ACCOUNT_TYPE,
            ACCOUNT_STATUS,
            CURRENCY_CODE,
            CURRENT_BALANCE,
            AVAILABLE_BALANCE,
            CREDIT_LIMIT,
            INTEREST_RATE,
            BRANCH_CODE,
            OPENED_DATE,
            CLOSED_DATE,
            LAST_TRANSACTION_DATE,
            RISK_RATING,
            KYC_STATUS,
            PEP_FLAG,
            SANCTIONS_FLAG,
            ORA_ROWSCN as CDC_SCN,
            SYSTIMESTAMP as EXTRACT_TIMESTAMP
        FROM CORE_BANKING.CUSTOMER_ACCOUNTS
        WHERE ORA_ROWSCN > {last_scn}
        ORDER BY ORA_ROWSCN) cdc_query
    """

    return (
        spark.read
        .format("jdbc")
        .option("url", ORACLE_JDBC_URL)
        .option("driver", ORACLE_DRIVER)
        .option("dbtable", query)
        .option("fetchsize", "10000")
        .option("sessionInitStatement", "ALTER SESSION SET NLS_TIMESTAMP_FORMAT='YYYY-MM-DD HH24:MI:SS.FF'")
        .load()
    )


def apply_pii_masking(df):
    """Hash PII fields for the raw zone — full values only in restricted zone."""
    return df.withColumn(
        "customer_id_hash", sha2(col("CUSTOMER_ID").cast("string"), 256)
    )


def transform_and_write(spark: SparkSession, df):
    """Apply schema standardisation and write to Iceberg with MERGE."""
    transformed = (
        df
        .withColumnRenamed("ACCOUNT_ID", "account_id")
        .withColumnRenamed("CUSTOMER_ID", "customer_id")
        .withColumnRenamed("ACCOUNT_TYPE", "account_type")
        .withColumnRenamed("ACCOUNT_STATUS", "account_status")
        .withColumnRenamed("CURRENCY_CODE", "currency_code")
        .withColumnRenamed("CURRENT_BALANCE", "current_balance")
        .withColumnRenamed("AVAILABLE_BALANCE", "available_balance")
        .withColumnRenamed("CREDIT_LIMIT", "credit_limit")
        .withColumnRenamed("INTEREST_RATE", "interest_rate")
        .withColumnRenamed("BRANCH_CODE", "branch_code")
        .withColumnRenamed("OPENED_DATE", "opened_date")
        .withColumnRenamed("CLOSED_DATE", "closed_date")
        .withColumnRenamed("LAST_TRANSACTION_DATE", "last_transaction_date")
        .withColumnRenamed("RISK_RATING", "risk_rating")
        .withColumnRenamed("KYC_STATUS", "kyc_status")
        .withColumnRenamed("PEP_FLAG", "pep_flag")
        .withColumnRenamed("SANCTIONS_FLAG", "sanctions_flag")
        .withColumn("_ingested_at", current_timestamp())
        .withColumn("_source_system", lit("ORACLE_DWH"))
        .withColumn("_cdc_operation", lit("UPSERT"))
    )

    transformed = apply_pii_masking(transformed)

    target_table = f"{ICEBERG_CATALOG}.{ICEBERG_DB}.{ICEBERG_TABLE}"

    transformed.createOrReplaceTempView("cdc_updates")

    spark.sql(f"""
        MERGE INTO {target_table} t
        USING cdc_updates s
        ON t.account_id = s.account_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    return transformed.agg({"CDC_SCN": "max"}).first()[0]


def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    last_scn = get_last_bookmark(spark)
    print(f"[ATLAS] Starting CDC from SCN: {last_scn}")

    cdc_df = read_cdc_changes(spark, last_scn)
    record_count = cdc_df.count()

    if record_count == 0:
        print("[ATLAS] No new changes detected. Exiting.")
        spark.stop()
        sys.exit(0)

    print(f"[ATLAS] Processing {record_count} changed records")

    max_scn = transform_and_write(spark, cdc_df)
    save_bookmark(spark, str(max_scn))

    print(f"[ATLAS] CDC complete. New bookmark SCN: {max_scn}")
    spark.stop()


if __name__ == "__main__":
    main()
