# Databricks notebook source
# MAGIC %md
# MAGIC # Synthetic healthcare: source assessment
# MAGIC
# MAGIC Read-only first step. Upload the synthetic CSV to a Unity Catalog volume,
# MAGIC enter its `/Volumes/.../healthcare_dataset.csv` path below, and run all cells.
# MAGIC No tables are created. The file contains synthetic names; results below
# MAGIC intentionally summarize records without displaying names or raw rows.

# COMMAND ----------

from pyspark.sql import functions as F

dbutils.widgets.text("source_path", "", "Synthetic CSV volume path")
source_path = dbutils.widgets.get("source_path").strip()
if not source_path.startswith("/Volumes/") or not source_path.lower().endswith(".csv"):
    raise ValueError("Enter the uploaded CSV's /Volumes/... path in the source_path widget.")

expected_columns = [
    "Name", "Age", "Gender", "Blood Type", "Medical Condition", "Date of Admission",
    "Doctor", "Hospital", "Insurance Provider", "Billing Amount", "Room Number",
    "Admission Type", "Discharge Date", "Medication", "Test Results",
]
raw = (spark.read.option("header", True).option("inferSchema", False)
       .option("mode", "FAILFAST").csv(source_path))
if raw.columns != expected_columns:
    raise ValueError("Source columns or their order changed; inspect the file before proceeding.")

# COMMAND ----------

# Count exact source-row repeats before trimming or converting any values.
source_rows = raw.count()
distinct_rows = raw.distinct().count()
print(f"Source records: {source_rows:,}")
print(f"Exact duplicate copies beyond the first: {source_rows - distinct_rows:,}")
print(f"Distinct complete source rows: {distinct_rows:,}")

# COMMAND ----------

# TRY_CAST returns null for invalid values even when ANSI mode is enabled.
profile = (raw
    .withColumn("_age", F.expr("try_cast(`Age` as int)"))
    .withColumn("_admitted", F.expr("try_cast(`Date of Admission` as date)"))
    .withColumn("_discharged", F.expr("try_cast(`Discharge Date` as date)"))
    .withColumn("_bill", F.expr("try_cast(`Billing Amount` as decimal(18, 2))")))
missing = F.lit(False)
for column in expected_columns:
    missing = missing | F.col(f"`{column}`").isNull() | (F.trim(F.col(f"`{column}`")) == "")

checks = profile.agg(
    F.sum(F.when(missing, 1).otherwise(0)).alias("rows_with_missing_values"),
    F.sum(F.when(F.col("_age").isNull() | ~F.col("_age").between(0, 120), 1).otherwise(0)).alias("invalid_age"),
    F.sum(F.when(F.col("_admitted").isNull() | F.col("_discharged").isNull(), 1).otherwise(0)).alias("invalid_dates"),
    F.sum(F.when(F.col("_discharged") < F.col("_admitted"), 1).otherwise(0)).alias("reversed_dates"),
    F.sum(F.when(F.col("_bill").isNull(), 1).otherwise(0)).alias("invalid_billing_amount"),
    F.sum(F.when(F.col("_bill") < 0, 1).otherwise(0)).alias("negative_billing_amount"),
    F.min("_admitted").alias("first_admission_date"),
    F.max("_admitted").alias("last_admission_date"),
)
display(checks)

# COMMAND ----------

# MAGIC %md
# MAGIC Counts above describe the complete source, including duplicates. A negative
# MAGIC bill is a review flag, not proof of an error. This synthetic file does not
# MAGIC establish reliable patient identities, readmissions, churn, or currency.
# MAGIC Compare results with the local source assessment before building curated tables.
