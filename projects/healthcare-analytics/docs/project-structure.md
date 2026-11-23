# Project structure

This guide describes the Databricks-to-Power BI project and its public documentation.

## Project files

- `README.md`: project overview, synthetic source assessment, processing rules, and interpretation limits.
- `docs/`: architecture visuals and this guide.
- `databricks/`: source assessment and curation notebooks and instructions for the cloud workflow. The notebooks assess the source and create the curated admissions and quality-summary tables.

## Local, Git-ignored data and results

- `data/raw/`: the synthetic source file.
- `results/`: local generated outputs and report work files. The current Databricks-connected working report is in `results/healthcare-databricks-design/`.

See the [Databricks guide](../databricks/README.md) and [architecture](architecture.md) for the current workflow and its limitations.
