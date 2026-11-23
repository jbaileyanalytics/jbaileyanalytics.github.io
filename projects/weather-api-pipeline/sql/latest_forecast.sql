-- Latest retrieved snapshot for each fictional planning location.
-- These are model forecasts, not observed weather or proof of operational disruption.
SELECT 
    location_code, 
    name, 
    retrieved_at_utc, 
    valid_at_utc,
    valid_at_utc AT TIME ZONE display_timezone AS valid_at_local,
    display_timezone, 
    temperature_c, 
    precipitation_probability_pct,
    precipitation_mm, 
    wind_speed_kmh
FROM latest_location_forecast
WHERE valid_at_utc >= CURRENT_TIMESTAMP
ORDER BY location_code, valid_at_utc;
