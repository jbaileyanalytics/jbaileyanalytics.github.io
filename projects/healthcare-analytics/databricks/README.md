# Databricks healthcare assessment

This folder contains the Databricks notebooks for the healthcare analytics project. `01_source_assessment.py` profiles the synthetic CSV without writing tables or displaying patient or clinician names. Its source and duplicate counts were confirmed in the Databricks workspace, along with the source negative-billing count.

1. In your Free Edition workspace, create or choose a Unity Catalog volume in your workspace catalog and default schema.
2. Upload the existing synthetic `healthcare_dataset.csv` from `data/raw/` to that volume through the workspace UI. Do not commit the raw file to the public repository.
3. Import `01_source_assessment.py` into a workspace folder as a notebook. Attach the notebook to the available serverless compute.
4. Enter its `/Volumes/<catalog>/<schema>/<volume>/healthcare_dataset.csv` path in the `source_path` widget and run the notebook. The actual catalog and volume names belong to your workspace; do not commit them or any credentials.
5. Compare the results to the inspected snapshot in the project README: 55,500 source rows, 534 duplicate copies, and 108 source rows with negative billing. The checks use the full source; retained counts use the deduplicated source.

The file is synthetic, and its billing currency and negative-bill meaning are not established. Excluding duplicate-looking rows is an explicit demonstration assumption. The notebook compares original text values before trimming. Different or malformed inputs may produce different results.

## Build curated tables

Import `02_curate_admissions.py` as a separate notebook. In its first code cell, set `source_path` to the same CSV path that worked in the source assessment and `target_schema` to the destination catalog and schema, for example `workspace.default` if that is your catalog. Run the cells in order. The notebook creates two managed Delta tables, `healthcare_curated_admissions_v1` and `healthcare_quality_summary_v1`, only after its pre-write checks pass. It refuses to overwrite either table. If the first write succeeds and the second fails, the first table remains; inspect the issue and choose new table names or deliberately clean up before rerunning.

The admissions table keeps one copy of each exact raw row, excludes distinct records that fail required-field/type/date rules, flags retained negative bills, and calculates elapsed stay days. It excludes patient and clinician names. Its deterministic hash identifies a distinct source row for this exercise, not a verified patient or a persistent warehouse identity. The quality table is an unfiltered snapshot summary, not a record-level quarantine. Duplicate and invalid records are counted, not saved into a quarantine table. Currency remains unspecified.

The project owner reported a successful Databricks run and confirmed the persisted summary: 55,500 source rows, 534 duplicate copies, 54,966 curated admissions, and 106 retained negative bills. These counts reconcile to zero invalid distinct rows. The notebook does not hard-code snapshot-specific counts; results may differ for revised input.

The first output is a denormalized admission table, not a dimensional model. Add dimensions only if they support a specific analytical need. The project owner connected Power BI Desktop to the Free Edition SQL warehouse, loaded both tables, and reported a successful refresh. This does not establish scheduled ingestion or a publicly hosted Power BI report.
