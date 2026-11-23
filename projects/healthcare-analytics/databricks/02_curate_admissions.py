# Databricks notebook source
# MAGIC %md
# MAGIC # Synthetic healthcare: curate and reconcile admissions
# MAGIC
# MAGIC Update the two configuration values below to match your workspace. This
# MAGIC notebook creates two new managed Delta tables and does not overwrite tables.
# MAGIC Run on the synthetic CSV only. No patient or clinician names are persisted.

# COMMAND ----------

from pyspark.sql import functions as F

# These are examples. Change them to your actual CSV path and target schema.
source_path = "/Volumes/<catalog>/default/healthcare_dataset/healthcare_dataset.csv"
target_schema = "<catalog>.default"

import re
if (not source_path.startswith("/Volumes/") or not source_path.lower().endswith(".csv")
        or "<" in source_path or not re.fullmatch(r"[A-Za-z0-9_]+\.[A-Za-z0-9_]+", target_schema)):
    raise ValueError("Set source_path and target_schema to your actual volume path and catalog.schema.")

admissions_table = f"{target_schema}.healthcare_curated_admissions_v1"
quality_table = f"{target_schema}.healthcare_quality_summary_v1"
for table in (admissions_table, quality_table):
    if spark.catalog.tableExists(table):
        raise ValueError(f"Target table already exists: {table}. Choose new table names before rerunning.")

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

# Compare the original source fields before trimming. Identical copies are
# treated as duplicates for this demonstration, not proven duplicate encounters.
source_count = raw.count()
unique_raw = raw.distinct()
unique_count = unique_raw.count()
duplicate_copies = source_count - unique_count
if source_count == 0:
    raise ValueError("The source file contains no records.")

# This deterministic technical identifier identifies the full original row;
# it is not a patient ID or proof of a real-world encounter identity.
source_identity = F.sha2(F.to_json(F.struct(*[F.col(f"`{c}`") for c in expected_columns]),
                                    options={"ignoreNullFields": "false"}), 256)
prepared = (unique_raw.withColumn("encounter_id", source_identity)
    .withColumn("_age", F.expr("try_cast(`Age` as int)"))
    .withColumn("_admitted", F.expr("try_cast(`Date of Admission` as date)"))
    .withColumn("_discharged", F.expr("try_cast(`Discharge Date` as date)"))
    .withColumn("_bill", F.expr("try_cast(`Billing Amount` as decimal(18, 2))")))
missing = F.lit(False)
for column in expected_columns:
    missing = missing | F.col(f"`{column}`").isNull() | (F.trim(F.col(f"`{column}`")) == "")
invalid = (missing | F.col("_age").isNull() | ~F.col("_age").between(0, 120)
           | F.col("_admitted").isNull() | F.col("_discharged").isNull()
           | (F.col("_discharged") < F.col("_admitted")) | F.col("_bill").isNull())
prepared = prepared.withColumn("_invalid", F.coalesce(invalid, F.lit(True)))
invalid_count = prepared.filter(F.col("_invalid")).count()
valid = prepared.filter(~F.col("_invalid"))

curated = valid.select(
    "encounter_id", F.col("_age").alias("age"),
    F.trim(F.col("Gender")).alias("gender"), F.trim(F.col("Blood Type")).alias("blood_type"),
    F.trim(F.col("Medical Condition")).alias("medical_condition"),
    F.col("_admitted").alias("admission_date"), F.col("_discharged").alias("discharge_date"),
    F.trim(F.col("Hospital")).alias("hospital"),
    F.trim(F.col("Insurance Provider")).alias("insurance_provider"),
    F.trim(F.col("Admission Type")).alias("admission_type"),
    F.trim(F.col("Medication")).alias("medication"),
    F.trim(F.col("Test Results")).alias("test_result"),
    F.col("_bill").alias("billing_amount"),
    (F.col("_bill") < 0).alias("negative_billing_flag"),
    F.datediff("_discharged", "_admitted").alias("length_of_stay_days"),
)

# COMMAND ----------

retained = curated.count()
negative = curated.filter(F.col("negative_billing_flag")).count()
if source_count != duplicate_copies + invalid_count + retained:
    raise ValueError("Source records did not reconcile; no tables were written.")
if curated.select("encounter_id").distinct().count() != retained:
    raise ValueError("Encounter identifiers are not unique; no tables were written.")
if curated.filter(F.col("length_of_stay_days") < 0).limit(1).count():
    raise ValueError("Negative length of stay detected; no tables were written.")

print(f"Source rows: {source_count:,}")
print(f"Duplicate copies excluded: {duplicate_copies:,}")
print(f"Invalid distinct rows excluded: {invalid_count:,}")
print(f"Curated admissions: {retained:,}")
print(f"Retained negative bills flagged: {negative:,}")

# COMMAND ----------

# New tables only. If a write fails after the first succeeds, resolve the partial
# output deliberately before rerunning; this notebook never drops tables.
quality = spark.createDataFrame([(source_count, duplicate_copies, invalid_count, retained, negative)],
    ["source_rows", "duplicate_copies_excluded", "invalid_distinct_rows_excluded",
     "curated_admissions", "retained_negative_bills"])
curated.write.format("delta").mode("error").saveAsTable(admissions_table)
quality.write.format("delta").mode("error").saveAsTable(quality_table)

# Verify persisted counts independently of the DataFrames used for the writes.
if spark.table(admissions_table).count() != retained or spark.table(quality_table).count() != 1:
    raise ValueError("Persisted table counts differ from the pre-write reconciliation.")
print(f"Created {admissions_table} and {quality_table}.")
display(spark.table(quality_table))

# COMMAND ----------

# MAGIC %md
# MAGIC The curated table is admission-grain and denormalized for this first step.
# MAGIC The quality table is a full-snapshot summary; it does not filter with admissions.
# MAGIC The source is synthetic, the currency is unspecified, and negative bills are
# MAGIC retained for review. This is not a patient identity, churn, or clinical outcome model.
