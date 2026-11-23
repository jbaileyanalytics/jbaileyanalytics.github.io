# Hospital Admissions, Billing and Data Quality Analytics

Status: the synthetic source was assessed and curated in Databricks. The project owner confirmed reconciliation of 55,500 source rows to 54,966 curated admissions, with 106 retained negative bills flagged. Power BI Desktop connected to the Databricks tables and refreshed successfully. The working report and connection details remain local; the portfolio case study offers screenshots and a separate downloadable report.

See the [Databricks workflow](databricks/README.md) and [architecture](docs/architecture.md).

`Synthetic CSV → Unity Catalog volume → PySpark assessment and curation → Delta tables → Power BI`

## Business question

How do admission volume, length of stay and billed amounts vary across admission types, medical conditions and insurers, and which source records require review?

Source: [Healthcare Dataset by prasad22 on Kaggle](https://www.kaggle.com/datasets/prasad22/healthcare-dataset). This is a synthetic demonstration. Findings describe these generated records and are not evidence about real healthcare organizations, care quality or treatment effectiveness. Currency is not specified by the inspected file; do not label billing as USD without supporting documentation.

## Verified source snapshot

Inspected November 12, 2026. Original CSV SHA-256: `d8c23c7dddaf0e1f5daf26182eb908c219d28a63bb574377c3ba6cb09be8a342`.

| Check | Result |
|---|---:|
| Source rows / columns | 55,500 / 15 |
| Exact duplicate copies excluded | 534 |
| Other invalid distinct rows excluded | 0 |
| Retained admission records | 54,966 |
| Missing source cells | 0 |
| Negative bills, original / retained | 108 / 106 |
| Admission dates | May 8, 2019-May 7, 2024 |
| Mean stay, retained records | 15.4993 days |

There are 39,876 distinct hospital labels after trimming for only 54,966 admissions. This makes a hospital league table a poor default and illustrates why synthetic source characteristics need inspection before business interpretation. Patient names are also not reliable identities. We count admission records and do not manufacture a unique-patient metric, readmission rate or churn label.

## Databricks processing rules

- Preserve the original CSV and its checksum locally.
- Exclude exact repeated source rows using all fifteen original fields; retain one copy. This is a documented project assumption, not proof that two identical real encounters are duplicates.
- Trim selected text fields without merging similar values. Patient and clinician names are used for exact source-row comparison but are not included in the curated tables.
- Exclude distinct records with missing required values, unparseable or reversed dates, invalid billing amounts, or ages outside 0-120. The inspected snapshot has no such distinct records.
- Keep negative billing amounts and flag them for review. Their meaning is unknown; they could not be classified as errors or refunds from this file alone.
- Derive stay length as discharge date minus admission date. A same-day stay has zero elapsed days. This is not an occupied-bed-day or capacity measure.
- Record duplicate and invalid counts in the quality summary; the Databricks workflow does not create a record-level quarantine table.

## Power BI report

The Databricks-connected working report presents admissions, billing and stay, and data quality on separate pages. Its connection and refresh were verified in Power BI Desktop. It imports a denormalized admissions table and a separate, full-snapshot quality summary; the report is not a connected star schema. The working project at `results/healthcare-databricks-design/HealthcareDatabricks.pbip` and its workspace-specific connection remain local and are excluded from Git.

The [portfolio case study](../../case-studies/healthcare-analytics.html) includes a separate Power BI Desktop download. It uses a fixed snapshot reconstructed locally from the inspected synthetic source using the project’s deduplication and validation approach. Its reconciliation and checked headline measures match the documented Databricks run; individual rows were not compared against the cloud tables. The download is not connected to Databricks and does not update with the cloud tables. Unneeded source fields and workspace connections are excluded.

Billed amounts are not collections, profit, or treatment costs. The first and last months are partial; do not compare them with complete months without that context. Test-result categories are recorded labels, not clinical outcomes or risk scores. Bed occupancy, readmissions, and patient retention cannot be calculated from these source fields alone.

The source does not establish patient identity, readmission, churn, or clinical outcomes. No predictive performance or clinical utility is claimed.

## Reproduce the Databricks workflow

Use the [Databricks setup guide](databricks/README.md) to upload the synthetic CSV to a Unity Catalog volume, run the read-only assessment, and create the curated and quality-summary tables. The CSV, workspace connection details, and working report remain local or workspace-specific and are excluded from Git.

