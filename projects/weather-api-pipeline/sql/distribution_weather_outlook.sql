-- Compare the next 24 forecast hours from each location's latest snapshot.
-- Thresholds are illustrative planning prompts, not operational alerts.
WITH next_24_hours AS (
    SELECT 
        location_code, 
        name, 
        retrieved_at_utc, 
        valid_at_utc,
        temperature_c, 
        precipitation_probability_pct, 
        wind_speed_kmh,
        ROW_NUMBER() OVER (PARTITION BY location_code ORDER BY valid_at_utc) AS hour_number
    FROM latest_location_forecast
    WHERE valid_at_utc >= retrieved_at_utc
), 
location_outlook AS (
    SELECT 
        location_code, 
        name, 
        MAX(retrieved_at_utc) AS retrieved_at_utc,
        COUNT(*) AS forecast_hours,
        ROUND(AVG(temperature_c)::numeric, 1) AS avg_temp_c,
        ROUND((AVG(temperature_c)::numeric * 9 / 5) + 32, 1) AS avg_temp_f,
        MAX(precipitation_probability_pct) AS peak_rain_chance_pct,
        ROUND(MAX(wind_speed_kmh)::numeric, 1) AS peak_wind_kmh,
        COUNT(*) FILTER (WHERE precipitation_probability_pct >= 60) AS hours_rain_chance_60_plus
    FROM next_24_hours
    WHERE hour_number <= 24
    GROUP BY location_code, name
)
SELECT 
    location_code, 
    forecast_hours, 
    avg_temp_c, 
    avg_temp_f, 
    peak_rain_chance_pct,
    peak_wind_kmh, 
    hours_rain_chance_60_plus,
    DENSE_RANK() OVER (ORDER BY peak_rain_chance_pct DESC NULLS LAST) AS rain_chance_rank
FROM location_outlook
ORDER BY rain_chance_rank, location_code;
