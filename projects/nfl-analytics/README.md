# NFL Player Performance and Ingestion Platform

Status: working local ingestion pipeline, dimensional model, and dashboard. No AWS deployment or scheduled cloud execution yet.

## Static dashboard preview

`website/` contains an independent browser-based NFL dashboard using validated season snapshots. From the portfolio root, run `python -m http.server 8769 --bind 127.0.0.1` and open `http://127.0.0.1:8769/projects/nfl-analytics/website/`. Serve it over HTTP; direct file access may not load data. The checked-in browser files provide a baseline without running ingestion. To regenerate them, first ingest the desired seasons as described below, then run `python projects/nfl-analytics/export_website.py`. The 2026 snapshot is in progress; raw source snapshots and other generated files remain ignored.

### Planned public refresh

The shared GitHub Pages workflow is configured to refresh the current NFL season on Tuesday and Thursday at approximately 6 a.m. Central, alongside the daily stock refresh. Thursday provides an opportunity to pick up nflverse corrections. A manually dispatched workflow also offers a `refresh_nfl` option. GitHub can delay scheduled runs, and source data may be incomplete or revised; these times do not guarantee fresh results.

Each run carries forward the currently published NFL season files so a stock-only update does not revert them. On first deployment, the checked-in browser snapshots provide the baseline. A new NFL download must pass schema and coverage checks, including previously published weeks and a 90% row/player coverage threshold. If the NFL refresh fails, the last validated baseline is retained and a workflow warning is recorded. If the published baseline cannot be safely read, or the stock build fails, deployment stops rather than replacing the site. These checks cannot prove that all games or corrections are present. The workflow and public refresh have not yet been deployed or verified on GitHub.

The website's player profile shows passing, rushing, or receiving production for a qualifying player within the selected season, weeks, teams, and position. Passing includes completions, completion rate, passing touchdowns, and interceptions; receiving includes receptions, catch rate, receiving touchdowns, and yards per target. Rates use totals divided by the appropriate total opportunities. Weekly yardage, highs, lows, and averages use only included player-week records; weeks without a record are displayed as gaps, not zero or confirmed missed games. The profile and comparison reflect the current minimum-opportunity filter and must not be treated as injury, availability, or causal analysis.

See the [architecture](docs/architecture.md) for the local flow. Automated checks are in `tests/`, and `model/` documents the separate local analytical model.

## Other local analysis

The Streamlit application remains available as a separate local example. An earlier Power BI report and its authoring files are retained locally and excluded from the public repository; they are not needed for the website or its refresh.

## Dimensional model

The local Streamlit application reads validated observations through a SQLite model. The static website instead reads exported browser JSON and does not require SQLite at runtime. The player-week fact joins stable player identities, observed name/position profiles, role-playing team and opponent dimensions, season-week context, and source snapshots. Trade history stays on each weekly observation, and changed inputs can be retained as separate revisions through the model CLI.

Review the [model documentation](model/README.md), [relationship diagram](model/model.svg), [schema and SQL views](model/schema.sql), and [analytical queries](model/queries.sql). SQL season totals demonstrate denominator-weighted efficiency; dashboard cohort calculations retain the existing aggregation rules. The dashboard model runs in memory; optional saved databases under `results/` are ignored by version control.

## Launch
From the parent `projects` folder:

```powershell
.\nfl-analytics\streamlit\run-dashboard.cmd
```

Open http://127.0.0.1:8504. An available local 2025 snapshot works offline; the application makes no network requests at startup. Snapshot data and its current pointer are excluded from Git, so a fresh checkout must obtain and prepare a snapshot using the instructions below. The launcher uses this project's `.venv`.

Independent setup requires Python 3.12. From this project directory, install dependencies and start the dashboard from its own folder so Streamlit reads its local theme configuration:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd streamlit
..\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8504
```

## Analytical purpose
Identify players combining workload and efficiency, compare production over selected weeks, and distinguish volume-driven yardage from yards gained per opportunity. The dashboard supports passing, rushing, and receiving as separate disciplines.

Views include weighted weekly efficiency, yardage leaders, opportunity/efficiency scatter, team contributions from the qualifying cohort, comparisons of up to four players, searchable leaderboards, exports, and data lineage.

## Real source data
The snapshots are derived from [nflverse weekly player statistics](https://github.com/nflverse/nflverse-data/releases/tag/stats_player), retrieved explicitly rather than scraped by the dashboard. The source is documented by [nflreadr](https://nflreadr.nflverse.com/reference/load_player_stats) and its [data dictionary](https://nflreadr.nflverse.com/articles/dictionary_player_stats.html).

The reviewed 2025 snapshot contains 19,422 original rows. Scope selection retains 6,037 regular-season QB/RB/WR/TE player-weeks, covering 610 distinct players and weeks 1-18. Other positions and postseason records account for the 13,385 excluded rows. These figures describe the reviewed snapshot and may change if the source is revised.

A separate 2026 snapshot retrieved on November 19, 2026, contains 10,446 source rows; 3,358 regular-season QB/RB/WR/TE player-weeks passed validation, covering 574 distinct players and weeks 1–10. The other 7,088 rows were excluded by season type or position. The 2026 season is in progress; the available weeks may be incomplete or revised and the snapshot is not a live feed. The season selector keeps each season's week range separate. Raw snapshots and their current pointers are local and Git-ignored; a fresh checkout must ingest the desired seasons to rebuild the website data. The separately prepared browser JSON files are eligible for publication.

This release uses box-score statistics, not Next Gen Stats tracking data. Next Gen Stats enrichment is future work and should be named only after the additional source is implemented.

## Reproduce ingestion
From this project directory, with dependencies installed:

```powershell
python ingest.py --season 2025
python ingest.py --season 2026
```

An explicit different season can be requested when nflverse publishes that release. The downloader builds a season-specific URL, uses a timeout and bounded retries, caps source size, and records retrieval time, source Last-Modified, and SHA-256. Source updates can revise historical statistics.

Pipeline flow:

```text
nflverse CSV -> content-hashed raw snapshot -> scope & schema validation
             -> sorted normalized CSV + week-partitioned Parquet
             -> metadata manifest -> atomic current-season pointer -> dashboard
```

Raw files are ignored by Git. Normalized snapshots and manifests are retained under `data/snapshots/season=YYYY/<content hash>/`. Each week has a `week=WW/player_stats.parquet` partition. The app verifies the normalized CSV checksum before analysis. Successful reprocessing of identical data reuses the same content-addressed path; invalid inputs do not advance the current pointer. This is local reproducibility, not S3 Object Lock or a production concurrency guarantee.

To rebuild an already-downloaded file without the network:

```powershell
python ingest.py --season 2025 --raw-file data/raw/<downloaded-file>.csv
```

The matching raw JSON metadata file is required and its checksum is checked.

## Metric definitions
- Passing opportunities = attempts; efficiency = passing yards / attempts.
- Rushing opportunities = carries; efficiency = rushing yards / carries.
- Receiving opportunities = targets; efficiency = receiving yards / targets.
- Catch rate = receptions / targets; completion rate = completions / attempts.
- Rates always use sums of numerators and denominators, not an average of weekly percentages. Zero denominators remain missing.
- Minimum workload applies over selected weeks/teams/positions. All overview charts use the same qualifying cohort. Team charts therefore represent cohort contributions, not full team statistics.
- Observed weeks count source player-week records, not roster-confirmed games played. Missing records are not fabricated as zero production; comparison charts retain gaps.
- Players are grouped by ID across trades. Latest team and all teams within scope are retained. A team filter includes only production recorded for that team.
- Passing and receiving yards are not added into a combined total.

## Validation and limits
Required columns, nonempty IDs, integer statistics, regular-season week bounds, requested season, nonnegative counts, completions <= attempts, receptions <= targets, and unique player-week keys are checked. Negative yardage is valid. Invalid offensive rows reject the dataset; intentional position/season-type exclusions are counted separately.

No fantasy scoring, betting recommendations, injury attribution, opponent adjustment, route participation, snap share, or projections are implemented. The GitHub refresh workflow is prepared but not yet verified in deployment. Current comparisons are descriptive and are not causal explanations or player scouting grades.

## Tests
With dependencies installed:

```powershell
python -m unittest discover -s tests -v
```

From the portfolio root in the current workspace:

```powershell
python -m unittest discover -s projects/nfl-analytics/tests -v
```

Tests cover weighted denominators, traded-player aggregation, negative yardage, invalid inputs, duplicate keys, repeatable publication, partition counts, failed-ingestion pointer preservation, snapshot checksums, UI filtering, and source-to-dashboard reconciliation.
Tests that require the local 2025 snapshot are skipped in a fresh checkout until it has been ingested. Source revisions can change the counts shown above.

## Next engineering stages
1. Verify the prepared scheduled refresh after publication and add a schedule-based completeness report; incomplete weeks must remain visibly provisional.
2. Add source-revision diffs and controlled correction history.
3. Add NGS enrichment with verified join keys and missingness reporting.
4. Deploy scheduled ingestion, S3 storage, monitoring, retries, and Athena access through Terraform.
5. Document deployment evidence, costs, analysis findings, and architectural tradeoffs for the portfolio case study.

## Attribution
Data: nflverse contributors. See [NOTICE.md](NOTICE.md) for source, license, and transformations. This is an independent portfolio project with no NFL affiliation.
