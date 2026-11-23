# Project structure

The project builds a historical stock-price website from Kaggle data. The checked-in website files are the application source; the stock data used by the website is generated separately during a local build or the prepared GitHub Pages workflow.

- `README.md`: setup, project status, source attribution, and limitations.
- `website/`: static dashboard, browser scripts and styling, and a local preview server and launcher.
- `pipelines/`: source profiling and acquisition, local SQLite build, reporting exports, optional Parquet audit, and Pages refresh and publication checks.
- `src/`: shared price calculations and historical summaries.
- `docs/`: source assessment, architecture, model, metric definitions, and source-to-target mappings.
- `notebooks/`: read-only source assessment notebook; source files must be obtained separately.
- `sql/`: source-coverage query for the local SQLite model.
- `tests/`: checks for calculations, processing, website behavior, and publication safeguards.
- `Dockerfile.batch` and `compose.batch.yaml`: the optional local Parquet and DuckDB batch comparison.

Downloaded data under the repository's `datasets/` folder, generated files under `results/`, and the detailed `docs/source-profile.json` are ignored by Git. A fresh checkout must obtain the Kaggle source and build the reporting data to run the full dashboard locally. The separate GitHub Actions workflow builds the stock website data for the Pages artifact; it has not yet been verified after deployment.
