# E-commerce retail lakehouse

A local data engineering and analytics project using seven historical e-commerce files from the [Kaggle dataset](https://www.kaggle.com/datasets/thedevastator/unlock-profits-with-e-commerce-sales-data). The pipeline preserves raw data in Parquet, applies validation and transformations with DuckDB and dbt, and produces reporting outputs.

**Status:** The seven-source build and data-quality reconciliation were verified locally. The Power BI report was refreshed and checked in Desktop. A separate, self-contained workbook is available from the portfolio case study.

`CSV files -> Python source inventory -> raw Parquet -> DuckDB + dbt -> local reporting files -> Power BI`

## Start here

- [Lakehouse setup and verification](lakehouse/README.md)
- [Current data model and mappings](lakehouse/DATA_MODEL.md)
- [Source assessment](docs/source-assessment.md)
- [Read-only source assessment notebook](notebooks/source_assessment.ipynb)
- [Business metric definitions](docs/business-metrics.md)
- [Architecture](docs/architecture.md) and [project structure](docs/project-structure.md)
- [Portfolio case study and Power BI download](../../case-studies/retail-lakehouse.html)
- [dbt models and tests](lakehouse/models/)

Run from the portfolio root after starting Docker Desktop:

```powershell
docker compose -f projects/ecommerce-domain/lakehouse/compose.yaml run --build --rm lakehouse
```

The original input files must be available in the local datasets folder. Raw Parquet and reporting outputs are ignored by Git and may contain identifiers. The pipeline does not depend on SQLite.

## Verified local results

In the verified local build, all seven source-row counts reconciled, 24 dbt data tests passed, and 15 models were constructed. The source contained 128,975 Amazon sales lines; 9,165 accepted and 106 rejected inventory records; 18,635 accepted and 18,797 rejected international records; 2,660 price-sheet rows and 30,590 price observations. Sales, inventory, product and price-quote IDs matched across two repeated runs of unchanged inputs.

Cancellation rates describe source sales lines, not unique orders or causation. The inventory file is undated. Expense and warehouse comparison sheets are source observations, not realized order-level costs. The dataset does not establish reliable profit, margin or fulfillment cost.

## Reporting

The Power BI report has sales and fulfillment, inventory, and data-quality pages. It includes sales month, fulfillment and category filters, a category cancellation count chart, and a fulfillment table showing rates with their underlying counts. The model uses separate sales, inventory and quality tables, not a connected star schema. The category count chart requires scrolling.

The completed working report project remains local under ignored `results/`. The case study includes screenshots and a separate downloadable Power BI Desktop report with a self-contained historical snapshot. Its source-order and source-row identifiers and local source paths have been removed; it does not automatically update with future runs.

The downloadable workbook was reopened in Power BI Desktop with the expected totals, and the sales-month filter was checked. It requires Power BI Desktop and contains imported historical data. Full cross-filter, blank-state and accessibility testing remains outstanding.
