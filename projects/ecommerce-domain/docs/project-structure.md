# Project structure

This guide maps the current local retail lakehouse and reporting work.

## Project files

- `README.md`: project overview, local run instructions, results, and reporting context.
- `docs/`: architecture diagrams, source assessment, business metric definitions, and this guide.
- `notebooks/source_assessment.ipynb`: read-only, aggregate-only source profiling and reproducible assessment checks. It includes saved aggregate results; rerunning it requires local source files.
- `lakehouse/`: the Docker-based ingestion and transformation project.
  - `run.py`, `Dockerfile`, `compose.yaml`, and `requirements.txt`: Python ingestion and the local container configuration.
  - `models/` and `tests/`: dbt staging and business models, along with SQL data tests.
  - `DATA_MODEL.md` and `README.md`: the current data model, mappings, setup, and limitations.
  - `powerbi/`: local, Git-ignored report-authoring scripts and design templates.
- `report_helpers.py`: local, Git-ignored helpers used by the report-authoring scripts.

## Local, Git-ignored results

- `results/lakehouse-direct/`: run-specific raw Parquet, DuckDB databases, reporting exports, and persistent ID registries. Back up the registries if existing IDs need to be retained between runs.
- `results/lakehouse-powerbi-professional/`: the retained, user-formatted Power BI project, including `Retail.pbip`. It uses local reporting outputs and is kept out of Git.

The original source files are kept separately in the local datasets folder. See the [lakehouse guide](../lakehouse/README.md) for run instructions and source limitations.
