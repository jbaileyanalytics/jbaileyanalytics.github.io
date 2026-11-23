-- PostgreSQL schema weather_data.
CREATE TABLE dim_location (
    location_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_code       TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    requested_latitude  NUMERIC(9,6) NOT NULL CHECK (requested_latitude BETWEEN -90 AND 90),
    requested_longitude NUMERIC(9,6) NOT NULL CHECK (requested_longitude BETWEEN -180 AND 180),
    display_timezone    TEXT NOT NULL
);

CREATE TABLE forecast_snapshot (
    forecast_snapshot_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id             BIGINT NOT NULL REFERENCES dim_location(location_id),
    capture_token           UUID NOT NULL UNIQUE,
    retrieved_at_utc        TIMESTAMPTZ NOT NULL,
    returned_latitude       NUMERIC(9,6) NOT NULL CHECK (returned_latitude BETWEEN -90 AND 90),
    returned_longitude      NUMERIC(9,6) NOT NULL CHECK (returned_longitude BETWEEN -180 AND 180),
    provider                TEXT NOT NULL,
    forecast_issue_time     TIMESTAMPTZ,
    UNIQUE (forecast_snapshot_id, location_id)
);

CREATE TABLE fact_hourly_forecast (
    hourly_forecast_id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    forecast_snapshot_id            BIGINT NOT NULL,
    location_id                     BIGINT NOT NULL REFERENCES dim_location(location_id),
    valid_at_utc                    TIMESTAMPTZ NOT NULL,
    temperature_c                   NUMERIC,
    precipitation_probability_pct   NUMERIC CHECK (precipitation_probability_pct BETWEEN 0 AND 100),
    precipitation_mm                NUMERIC CHECK (precipitation_mm >= 0),
    wind_speed_kmh                  NUMERIC CHECK (wind_speed_kmh >= 0),
    FOREIGN KEY (forecast_snapshot_id, location_id) REFERENCES forecast_snapshot(forecast_snapshot_id, location_id),
    UNIQUE (forecast_snapshot_id, valid_at_utc)
);
