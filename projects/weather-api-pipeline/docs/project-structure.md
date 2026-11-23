# Project structure

This project collects and validates hourly forecasts, stores retrieval snapshots in PostgreSQL, and runs a local daily schedule with Docker Compose.

- `README.md`: setup, scheduling, manual queries, verification, and source attribution.
- `config/`: example planning locations and time zones used by the pipeline.
- `pipelines/`: manual API inspection, individual forecast loading, and the daily scheduler.
- `src/`: forecast fetching and validation, batch execution, and PostgreSQL storage.
- `sql/`: database schema, additive migration, and example forecast and run-history queries.
- `tests/`: validation, scheduler, and disposable PostgreSQL integration tests.
- `docs/`: architecture, data model, source assessment, project scope, and verification evidence.
- `notebooks/`: read-only assessment of an existing local API capture.
- `Dockerfile`, `compose.yaml`, and `requirements.txt`: reproducible local services and Python dependency.
- `.env.example`: a non-secret configuration template; copy it to an ignored `.env` and set a unique local database password.

Local captures in `results/`, the filled-in `.env`, and database data in Docker's named volume are not published. The separately drafted `weather-api-cloud/` project is also excluded from Git and is not required for this local pipeline.
