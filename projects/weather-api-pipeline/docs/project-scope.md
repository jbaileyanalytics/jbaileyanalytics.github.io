# Project scope and decisions

## Why this project

This project complements the portfolio's file-based e-commerce and historical stock projects by demonstrating an external API, a recurring schedule, relational storage, and operational monitoring. The engineering evidence should include API contracts, documented grain, reproducible container setup, safe reruns, test results, data-quality checks, and an explanation of failures and recovery.

## Business scenario

Working assumption: an operations team plans staffing and outbound deliveries across a fictional ten-location distribution network. The pipeline supplies temperature, precipitation, and wind forecasts so the team can identify locations and time windows worth reviewing. The sample analysis uses an illustrative precipitation-probability threshold, not a validated operational alert. Forecasts indicate conditions to investigate; they do not establish that a disruption, delay, or loss occurred.

## Technical scope

- Python acquisition and transformation with explicit timeouts, bounded retries, and observable errors.
- A configurable list of locations and weather variables; avoid committing credentials or sensitive configuration.
- PostgreSQL tables with clear grains, `_id` surrogate identifiers where appropriate, constraints, and concise documentation of field transformations.
- Docker Compose for reproducible local services if Docker is available. Store persistent database data in a named volume; document lifecycle and avoid destructive cleanup commands.
- Daily scheduled execution and an overlap lock. Replaying the same capture is idempotent; distinct retrievals are retained as separate snapshots, with automated correction comparison still to be designed.
- Operational run and location logs separate from business-facing facts; validation rejects malformed responses without storing field-level quality findings.
- Optional business reporting only after defining the decision and confirming that the data supports it.

## Decisions to resolve

- Whether the example locations, planning thresholds, and two-day forecast horizon suit a real operational use case.
- Whether to extend beyond the current Open-Meteo forecast endpoint, requested units and variables, and noncommercial data terms.
- Forecast revision comparison and retention, including whether a provider issuance time is available for future use.
- Whether backfill, a different schedule, external alerts, or cloud deployment are needed for a future release.

## Out of scope until designed and verified

Claims of production deployment, real-time weather-station observations, actual operational outcomes, predictive accuracy, or financial savings. A weather API response alone does not establish those outcomes.
