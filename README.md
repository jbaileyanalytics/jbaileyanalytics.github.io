# John Bailey II | Data Engineering & Analytics

I build and analyze data systems that connect source data to useful reporting. This repository contains the source for my portfolio website and a collection of projects spanning data engineering, cloud analytics, data quality, and business intelligence.

My professional background includes financial services data engineering, vendor performance analytics, and healthcare quality reporting. These projects demonstrate how I approach ingestion, validation, transformation, analysis, and communication.

## Featured projects

| Project | Focus | Tools | Explore |
| --- | --- | --- | --- |
| **Weather API Pipeline** | Scheduled API ingestion, validation, and queryable forecast snapshots for a fictional distribution network. | Python, REST API, PostgreSQL, Docker | [Project](projects/weather-api-pipeline/README.md) · [Case study](case-studies/weather-api-pipeline.html) |
| **Retail Lakehouse** | Transform and reconcile seven historical e-commerce source files into sales, inventory, and quality reporting. | Python, Parquet, DuckDB, dbt, Power BI | [Project](projects/ecommerce-domain/README.md) · [Case study](case-studies/retail-lakehouse.html) |
| **Healthcare Analytics** | Assess and curate synthetic admissions data in Databricks, then explore admissions, billing, and quality in Power BI. | Databricks, PySpark, Delta, Power BI | [Project](projects/healthcare-analytics/README.md) · [Case study](case-studies/healthcare-analytics.html) |
| **Stock Market Analytics** | Process historical stock-price files and explore session movers and price history in an interactive website. | Python, SQLite, Parquet, DuckDB, JavaScript | [Project](projects/stock-market-analytics/README.md) |
| **NFL Player Analytics** | Analyze weekly player production, workload, and efficiency using validated nflverse snapshots. | Python, SQL, nflverse, JavaScript | [Project](projects/nfl-analytics/README.md) · [Dashboard](projects/nfl-analytics/website/) |

Project documentation describes the data, verification performed, and important limitations. The healthcare data is synthetic; stock data is historical rather than a live market feed; NFL results reflect available source snapshots. These projects do not claim real-world business outcomes from their demonstration datasets.

## Repository guide

- [`index.html`](index.html) and [`projects.html`](projects.html): portfolio homepage and project directory.
- [`case-studies/`](case-studies/): project explanations, selected results, and static evidence.
- [`projects/`](projects/): source code, project documentation, and applicable report definitions.
- [`images/projects/`](images/projects/): portfolio illustrations and reviewed report screenshots.

The weather, retail, stock, and NFL implementations were developed and tested locally. The healthcare project also includes a Databricks Free Edition workflow and a Power BI Desktop connection whose refresh was verified. The shared GitHub Pages workflow for stock and NFL refreshes is prepared but has not yet been verified after publication. Project status and limitations are documented in the individual READMEs.

## Working with the projects

Each project has its own setup and prerequisites. Source datasets, local databases, generated outputs, credentials, private study notes, and workspace-specific connection details are excluded from Git where configured. Some projects require separate datasets or accounts; consult their READMEs before running them. Dataset attribution and redistribution terms should be reviewed for any shared data or generated artifacts.

## Connect

- [Portfolio](https://jbaileyanalytics.github.io/)
- [LinkedIn](https://www.linkedin.com/in/john-bailey-ii-8b7713126/)
- [Email](mailto:jbaileyanalytics@gmail.com)
