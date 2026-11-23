# Retail lakehouse

**Status:** The pipeline runs locally in Docker and processes seven Kaggle CSV files through Python, raw Parquet, DuckDB, and dbt. The completed Power BI report has been refreshed and checked locally. The portfolio currently presents reviewed screenshots; interactive embedding is a possible future enhancement.

```text
Seven CSV sources -> Python inventory and SHA-256 -> raw Parquet
                  -> DuckDB + dbt validation and models -> local reporting exports
                  -> separate local Power BI report
```

## Run

Start Docker Desktop, then from the repository root:

```powershell
docker compose -f projects/ecommerce-domain/lakehouse/compose.yaml run --build --rm lakehouse
```

The source files must be placed in the local `datasets/E-Commerce Sales Dataset/` folder at the repository root. Each run has a separate directory under the project’s `results/lakehouse-direct/` folder. Raw Parquet preserves the original source fields, potentially including identifying fields; the entire results directory is Git-ignored.

## Sources and reconciliation

The data-quality mart reconciles source counts against accepted and rejected records. Amazon, inventory and international sales are validated. The two price sheets, expense file and warehouse comparison are retained as source rows; retaining a row does not certify its business meaning. International customer names are excluded from the modeled sales output.

A verified run reconciled 128,975 Amazon records; 9,271 inventory records (9,165 accepted, 106 rejected); 37,432 international records (18,635 accepted, 18,797 rejected); two price sheets of 1,330 records each; 17 expense records; and 50 warehouse comparison records. There is no evidence linking the price and warehouse sheets to realized order-level profit.

## IDs and limitations

The persistent product registry assigns increasing IDs by normalized SKU. A separate persistent entity registry assigns increasing source-row IDs using the source file hash and record position. Repeating an unchanged file reuses its ID. If the file changes, its hash changes and its source rows receive new IDs; this is snapshot identity, not a reliable business key or incremental correction mechanism. Both registries live under ignored output and must be backed up to retain IDs. Concurrent runs and recovery of partially assigned registry entries have not been validated.

See [DATA_MODEL.md](DATA_MODEL.md) for the current model and DuckDB/dbt mappings. Price observations are unpivoted into a separate quote table; a repeated run verified their IDs for unchanged inputs. The Power BI report imports separate sales, inventory, and source-quality tables; its model is not a connected star schema.


## Power BI report

The completed local report is kept at `results/lakehouse-powerbi-professional/Retail.pbip` relative to the project folder. It has sales and fulfillment, inventory, and data-quality pages; the sales page includes month, fulfillment, and category filters. Its model refers to a particular local reporting snapshot, and the report project and report-authoring scripts are excluded from Git.

The [portfolio case study](../../../case-studies/retail-lakehouse.html) presents report screenshots and a downloadable Power BI Desktop workbook. The download uses a self-contained historical snapshot, with local source paths and source-order and source-row identifiers removed; it does not automatically update with future lakehouse runs. A publicly embedded report is a future option. See the [project README](../README.md#reporting) for report context and testing limitations.
