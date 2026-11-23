-- Review completed runs and location-level outcomes independently.
SELECT 
    run_token, 
    started_at_utc, 
    finished_at_utc,
    status,
    locations_total, 
    locations_succeeded, 
    locations_failed, 
    rows_loaded, 
    error_message
FROM pipeline_run
ORDER BY started_at_utc DESC;

SELECT 
    r.run_token, 
    l.location_code, 
    l.status, 
    l.rows_loaded, 
    l.capture_token, 
    l.error_message
FROM pipeline_run_location l 
JOIN pipeline_run r USING (pipeline_run_id)
ORDER BY r.started_at_utc DESC, l.location_code;
