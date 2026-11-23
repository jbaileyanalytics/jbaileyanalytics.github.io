# Preliminary source assessment

## Candidate: Open-Meteo

[Open-Meteo](https://open-meteo.com/en/docs) offers a JSON weather API with location, time, and variable parameters. Its public service is described as free for noncommercial use without an API key, subject to provider limits and attribution; see the [provider's pricing and usage terms](https://open-meteo.com/en/pricing). Confirm the current terms for the intended portfolio use before publishing or scheduling.

The [forecast API documentation](https://open-meteo.com/en/docs) describes current and forecast variables and time-zone options. The [historical weather API](https://open-meteo.com/en/docs/historical-weather-api) provides model-based reanalysis data that combines observations with modeling; it should not be described as a direct weather-station measurement. A forecast and a historical estimate are different products and must not be merged as interchangeable facts.

## Initial response inspection

The [read-only source assessment notebook](../notebooks/source_assessment.ipynb) inspects a local captured response and reuses the pipeline's validation without making a request or writing to the database. Forecast responses change, so a later capture will not reproduce the exact values from the initial observation below.

On November 18, 2026, a Chicago example request to `/v1/forecast` returned hourly arrays for temperature, precipitation probability, precipitation, and wind speed. The response used `GMT` and offset zero, with units `°C`, `%`, `mm`, and `km/h`; 24 hourly values were observed in the one-day sample. The requested coordinates were `41.8781, -87.6298`, while the returned grid coordinates were `41.879498, -87.64974`. A later two-day run through the project's fetcher validated 48 hourly values. These are individual observations, not a completeness or reliability guarantee.

The [forecast documentation](https://open-meteo.com/en/docs) describes precipitation and its probability for the preceding hour. The operational forecast can combine model outputs; a retrieval timestamp must not be presented as a verified model issuance time.

## Current implementation and remaining questions

- The pipeline requests two days for ten configured locations, stores forecast times in UTC, validates nulls and response structure, and records partial location failures. The sample query converts times using each location's configured time zone.
- Confirm the provider's model, publication timing, forecast-update behavior, limits, attribution, and allowed usage for the selected endpoint.
- Continue investigating whether a reliable forecast issue time or model-run identifier is available. Retrieval snapshots do not establish provider-issued forecast versions.
- Define an automated process for comparing provider revisions and handling missed scheduled runs.

Open-Meteo is the source for the local pipeline. No ongoing availability, global coverage, or forecast accuracy has been established.
