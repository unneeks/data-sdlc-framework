"""
Project ATLAS — Risk Scores Batch Ingestion
Daily batch job that reads risk model outputs (credit, market, operational)
from the Risk Engine's output files and loads into Iceberg.

Source: s3://meridian-bank-risk-engine/outputs/{run_date}/
Target: glue_catalog.raw_banking.risk_scores
Schedule: Daily 06:00 UTC (after Risk Engine nightly run completes)
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, lit, input_file_name, regexp_extract,
    when, coalesce
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DecimalType,
    TimestampType, IntegerType, DateType
)
import sys
from datetime import date, timedelta

ICEBERG_CATALOG = "glue_catalog"
ICEBERG_DB = "raw_banking"
ICEBERG_TABLE = "risk_scores"
S3_WAREHOUSE = "s3://meridian-bank-raw/iceberg"
RISK_ENGINE_OUTPUT = "s3://meridian-bank-risk-engine/outputs"

RISK_SCORE_SCHEMA = StructType([
    StructField("score_id", StringType(), False),
    StructField("entity_id", StringType(), False),
    StructField("entity_type", StringType(), False),
    StructField("risk_type", StringType(), False),
    StructField("model_id", StringType(), False),
    StructField("model_version", StringType(), False),
    StructField("score_value", DecimalType(10, 6), False),
    StructField("score_band", StringType(), True),
    StructField("probability_of_default", DecimalType(10, 8), True),
    StructField("loss_given_default", DecimalType(10, 8), True),
    StructField("exposure_at_default", DecimalType(18, 4), True),
    StructField("expected_loss", DecimalType(18, 4), True),
    StructField("risk_weighted_assets", DecimalType(18, 4), True),
    StructField("confidence_interval_lower", DecimalType(10, 6), True),
    StructField("confidence_interval_upper", DecimalType(10, 6), True),
    StructField("feature_importance", StringType(), True),
    StructField("calculation_timestamp", TimestampType(), False),
    StructField("effective_date", DateType(), False),
    StructField("expiry_date", DateType(), True),
    StructField("regulatory_framework", StringType(), True),
])


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("atlas-risk-scores-batch")
        .config("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.glue_catalog.warehouse", S3_WAREHOUSE)
        .config("spark.sql.catalog.glue_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog")
        .config("spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .getOrCreate()
    )


def get_run_date() -> str:
    """Determine the run date — defaults to yesterday for morning batch."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return (date.today() - timedelta(days=1)).isoformat()


def read_risk_outputs(spark: SparkSession, run_date: str):
    """Read all risk model output files for the given date."""
    source_path = f"{RISK_ENGINE_OUTPUT}/{run_date}/"

    return (
        spark.read
        .schema(RISK_SCORE_SCHEMA)
        .option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", "_corrupt_record")
        .parquet(source_path)
        .withColumn("_source_file", input_file_name())
        .withColumn("_risk_model_type",
                    regexp_extract(input_file_name(), r"/(credit|market|operational)/", 1))
    )


def apply_regulatory_classification(df):
    """Tag scores with Basel III/IV regulatory classification."""
    return df.withColumn(
        "regulatory_treatment",
        when(col("risk_type") == "CREDIT",
             when(col("regulatory_framework") == "IRB_ADVANCED", "A-IRB")
             .when(col("regulatory_framework") == "IRB_FOUNDATION", "F-IRB")
             .otherwise("STANDARDISED"))
        .when(col("risk_type") == "MARKET", "FRTB_SA")
        .when(col("risk_type") == "OPERATIONAL", "BIA")
        .otherwise("UNCLASSIFIED")
    )


def validate_scores(df):
    """Validate risk scores are within acceptable bounds."""
    return df.withColumn(
        "_quality_flag",
        when(
            (col("score_value") < 0) | (col("score_value") > 1),
            "OUT_OF_RANGE"
        ).when(
            col("probability_of_default").isNotNull() &
            ((col("probability_of_default") < 0) | (col("probability_of_default") > 1)),
            "INVALID_PD"
        ).otherwise("VALID")
    )


def write_to_iceberg(spark: SparkSession, df, run_date: str):
    """Write validated risk scores to Iceberg with partition overwrite."""
    target = f"{ICEBERG_CATALOG}.{ICEBERG_DB}.{ICEBERG_TABLE}"

    enriched = (
        df
        .withColumn("_ingested_at", current_timestamp())
        .withColumn("_source_system", lit("RISK_ENGINE"))
        .withColumn("_run_date", lit(run_date))
    )

    enriched = apply_regulatory_classification(enriched)
    enriched = validate_scores(enriched)

    valid = enriched.filter(col("_quality_flag") == "VALID")
    invalid = enriched.filter(col("_quality_flag") != "VALID")

    if invalid.count() > 0:
        print(f"[ATLAS] WARNING: {invalid.count()} records failed validation")
        (invalid.write
         .mode("append")
         .parquet(f"s3://meridian-bank-raw/quarantine/risk_scores/{run_date}/"))

    (valid
     .writeTo(target)
     .overwritePartitions())

    return valid.count(), invalid.count()


def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    run_date = get_run_date()
    print(f"[ATLAS] Risk scores batch ingestion for date: {run_date}")

    risk_df = read_risk_outputs(spark, run_date)
    total_records = risk_df.count()
    print(f"[ATLAS] Read {total_records} risk score records")

    if total_records == 0:
        print("[ATLAS] No risk score outputs found. Check Risk Engine completion status.")
        spark.stop()
        sys.exit(1)

    valid_count, invalid_count = write_to_iceberg(spark, risk_df, run_date)

    print(f"[ATLAS] Ingestion complete: {valid_count} valid, {invalid_count} quarantined")
    spark.stop()


if __name__ == "__main__":
    main()
