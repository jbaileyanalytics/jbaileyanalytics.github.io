# Project structure

The project includes a static player analytics website and separate local Streamlit and Power BI analysis paths.

## Project files

- `README.md` and `NOTICE.md`: project setup, data scope, limitations, and source attribution.
- `docs/`: architecture visuals and this guide.
- `fetch_source.py` and `ingest.py`: acquire, validate, and publish local nflverse season snapshots.
- `pipeline.py` and `warehouse.py`: prepare player-week data and support the local SQLite analytical model.
- `export_website.py` and `prepare_published_data.py`: prepare the static dashboard's browser data and the planned publication workflow's season files.
- `website/`: the interactive static dashboard. The explicitly allowed `data/2025.json`, `data/2026.json`, and `data/seasons.json` files provide its checked-in baseline; other files in `website/data/` are ignored.
- `streamlit/`: the separate local Streamlit dashboard, its styling and configuration, and its Windows launcher. It uses shared processing code and local snapshots from the project root.
- `model/`: model documentation, relationship diagram, schema, analytical queries, and source mapping.
- `powerbi/`: an older Power BI report and authoring files retained locally and excluded from the public repository. They are not required by the static dashboard.
- `tests/`: checks covering the pipeline, model, dashboard, website export, and publication data preparation.
- `requirements.txt`: Python dependencies for the project.

## Local, Git-ignored data and results

- `data/raw/`, `data/snapshots/`, and `data/current_*.json`: downloaded source files, versioned local snapshots, and current-snapshot pointers.
- `results/`: generated local outputs and optional saved databases.

The scheduled GitHub Pages refresh is prepared but has not yet been verified on GitHub. See the [project README](../README.md) and [architecture](architecture.md) for setup and limitations.
