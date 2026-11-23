# Verification evidence

## Ten-location run on November 19, 2026

A user-provided terminal screenshot shows a PostgreSQL run-history query with a successful run starting at **12:30:00 p.m. Central** on November 19, 2026: ten locations succeeded, none failed, and 480 hourly rows were loaded. That timestamp matches the current 12:30 p.m. Central scheduler configuration. The same screenshot shows a query returning 20 Denver forecast rows from the latest-location view. [View the terminal evidence](../../../images/projects/weather-scheduled-run.png).

The database record verifies the reported start time and result; the screenshot alone does not prove which process initiated the run. Earlier scheduler logs separately document the three-location timer test. The November 18 schedule references below describe the configuration and observations at that earlier time, before the change to 12:30 p.m. Central.

## Local verification on November 18, 2026

- A manually initiated run retrieved and loaded forecasts for three fictional planning locations: 48 hours for each, 144 hourly rows in total. The run record reported three successes and no failures.
- The `latest_location_forecast` view returned the latest snapshot for each location. The sample SQL query also returned UTC and local-time fields from the stored data.
- Eleven automated tests passed in a disposable PostgreSQL container. They cover API validation and bounded retries, schema constraints, transaction rollback on invalid data, idempotent and conflicting capture replay, a simulated partial API failure and subsequent recovery, a simulated unavailable database, the overlap lock, and simulated scheduler timing.
- A separate scheduler was pointed at the disposable database with a near-term UTC schedule. At the target time, it ran the real batch, successfully loaded 48 hours for each of the three locations, and scheduled its next run. The temporary test services were stopped afterward; the project database and daily scheduler were left running.
- The project scheduler's configured next execution was observed as November 19, 2026, at 13:00 UTC. That specific daily execution had not yet occurred at the time of this review.

## One-time scheduled verification on November 18, 2026

A separate instance of the project scheduler was temporarily set to 18:13 UTC and ran against the local project database. The scheduler log recorded the target time and a successful run; the database recorded a start at 18:13:00 UTC and completion at 18:13:01 UTC. ATL, CHI, and DFW each loaded 48 hourly forecasts: 144 total, with zero failed locations. The temporary scheduler was stopped after verification. The normal scheduler remained running and retained its 13:00 UTC daily schedule. This is a one-time scheduled verification, not evidence of the subsequent regular daily execution.

The distribution outlook query in sql/distribution_weather_outlook.sql was run against those latest snapshots. It returned 24 hours per location: ATL average 13.3 °C, peak rain probability 4%, peak wind 18.8 km/h; CHI 9.1 °C, 1%, 21.4 km/h; DFW 14.5 °C, 1%, 9.8 km/h. All three had zero hours at or above the illustrative 60% precipitation-probability threshold. These are forecasts, and the query output will change as new snapshots arrive.

## Expanded network verification on November 18, 2026

A manually initiated run at 18:21 UTC processed all ten configured locations successfully, with 48 hourly forecasts per location, 480 records total, and zero failures. The scheduler was rebuilt with the updated configuration and its next daily run was recorded as November 19 at 13:00 UTC. This ten-location run was manual; the earlier scheduled verification above used three locations.

## Interpretation and limitations

These checks establish local behavior for the tested scenarios, not uptime, forecast accuracy, cloud deployment, production readiness, or business impact. The project does not provide external alerts, automatic backfill of missed schedules, or a retention policy. It needs Docker Desktop and the computer running to execute. Database failures before run tracking can connect are visible in container logs, not in the database audit tables. API values are provider forecasts rather than actual station observations.
