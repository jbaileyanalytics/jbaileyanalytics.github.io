-- Safe, additive migration for existing or newly initialized project databases.
CREATE TABLE IF NOT EXISTS pipeline_run (
    pipeline_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_token UUID NOT NULL UNIQUE,
    started_at_utc TIMESTAMPTZ NOT NULL,
    finished_at_utc TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running','succeeded','partial','failed','skipped_overlap')),
    locations_total INTEGER NOT NULL CHECK (locations_total >= 0),
    locations_succeeded INTEGER NOT NULL DEFAULT 0 CHECK (locations_succeeded >= 0),
    locations_failed INTEGER NOT NULL DEFAULT 0 CHECK (locations_failed >= 0),
    rows_loaded INTEGER NOT NULL DEFAULT 0 CHECK (rows_loaded >= 0),
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS pipeline_run_location (
    pipeline_run_location_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_run_id BIGINT NOT NULL REFERENCES pipeline_run(pipeline_run_id),
    location_code TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('succeeded','failed')),
    capture_token UUID,
    forecast_snapshot_id BIGINT REFERENCES forecast_snapshot(forecast_snapshot_id),
    rows_loaded INTEGER NOT NULL DEFAULT 0 CHECK (rows_loaded >= 0),
    error_message TEXT,
    UNIQUE (pipeline_run_id, location_code)
);
CREATE OR REPLACE VIEW latest_location_forecast AS
WITH latest AS (
    SELECT DISTINCT ON (location_id) forecast_snapshot_id, 
        location_id, 
        retrieved_at_utc
    FROM forecast_snapshot
    ORDER BY location_id, retrieved_at_utc DESC, forecast_snapshot_id DESC
)
SELECT 
    l.location_code,
    l.name,
    l.display_timezone, 
    s.retrieved_at_utc,
    f.valid_at_utc, 
    f.temperature_c, 
    f.precipitation_probability_pct,
    f.precipitation_mm, 
    f.wind_speed_kmh
FROM latest s 
JOIN dim_location l ON l.location_id=s.location_id
JOIN fact_hourly_forecast f ON f.forecast_snapshot_id=s.forecast_snapshot_id;
