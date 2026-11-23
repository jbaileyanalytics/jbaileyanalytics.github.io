# NFL player performance: source to analytical products

## 1. Source field mappings

| Source dataset | Source column | Validated logical type | Target / key lookup | Transformation |
| --- | --- | --- | --- | --- |
| player_week.csv | player_id | TEXT | dim_player.player_id → fact.player_key | Distinct trimmed IDs; generate stable player surrogate |
| player_week.csv | player_display_name | TEXT | dim_player_profile.player_display_name → fact.profile_key | Preserve reported name; profile lookup includes player and position |
| player_week.csv | position | TEXT | dim_player_profile.position → fact.profile_key | Scope QB/RB/WR/TE; preserve observed position |
| player_week.csv | season | INTEGER | dim_season_week.season → fact.week_key | Validate 1999–2100 and expected season if supplied |
| player_week.csv | week | INTEGER | dim_season_week.week → fact.week_key | Validate REG week 1–18; lookup includes season/type |
| player_week.csv | season_type | TEXT | dim_season_week.season_type → fact.week_key | Select REG; count excluded scope records separately |
| player_week.csv | game_id | TEXT | fact_player_week.game_id | Retain source game identifier as degenerate dimension |
| player_week.csv | team | TEXT | dim_team.team_code → fact.team_key | Distinct source code; team role on each weekly fact |
| player_week.csv | opponent_team | TEXT | dim_team.team_code → fact.opponent_team_key | Same team dimension in opponent role |
| player_week.csv | completions | INTEGER | fact_player_week.completions | Validate integer; nonnegative count |
| player_week.csv | attempts | INTEGER | fact_player_week.attempts | Validate integer; nonnegative count |
| player_week.csv | passing_tds | INTEGER | fact_player_week.passing_tds | Validate integer; nonnegative count |
| player_week.csv | passing_interceptions | INTEGER | fact_player_week.passing_interceptions | Validate integer; nonnegative count |
| player_week.csv | carries | INTEGER | fact_player_week.carries | Validate integer; nonnegative count |
| player_week.csv | rushing_tds | INTEGER | fact_player_week.rushing_tds | Validate integer; nonnegative count |
| player_week.csv | targets | INTEGER | fact_player_week.targets | Validate integer; nonnegative count |
| player_week.csv | receptions | INTEGER | fact_player_week.receptions | Validate integer; nonnegative count |
| player_week.csv | receiving_tds | INTEGER | fact_player_week.receiving_tds | Validate integer; nonnegative count |
| player_week.csv | passing_yards | INTEGER | fact_player_week.passing_yards | Validate integer; negative yardage allowed |
| player_week.csv | rushing_yards | INTEGER | fact_player_week.rushing_yards | Validate integer; negative yardage allowed |
| player_week.csv | receiving_yards | INTEGER | fact_player_week.receiving_yards | Validate integer; negative yardage allowed |


## 2. Generated fields and reference tables

| Target | Origin / rule |
| --- | --- |
| dim_player.player_key | Generated surrogate integer for stable source player_id |
| dim_player_profile.profile_key / player_key | Generated observed-profile key; stable player lookup; unique player/name/position |
| dim_team.team_key | Generated surrogate for distinct team and opponent codes combined |
| dim_season_week.week_key | Generated surrogate for distinct season/type/week; not an ISO calendar week |
| model_snapshot.* | Generated snapshot_key, canonical normalized-content hash, first payload hash, accepted-row count, UTC load time |
| fact_player_week.snapshot_key | Current source snapshot; select one revision for analysis |


## 3. Published products

| Table / view | Product | Use |
| --- | --- | --- |
| fact_player_week | Weekly performance data product | Trace each count and yard total to player/week, team/opponent and source snapshot |
| v_player_week | Reconstructed analytical detail | Restore source identities through unique dimension joins; feed dashboard cohort calculations |
| v_player_season_totals | Season-level reporting product | Aggregate observed weeks and production; compute denominator-weighted efficiency |


## 4. Grain and modeling decisions

- The input is already at player-week grain. Modeling separates repeating identities and observed attributes while retaining source measures on one weekly fact.

- The player dimension uses stable IDs, not names. A trade changes the fact's team key; it does not change player identity or rewrite earlier team production.

- Player profiles preserve observed name/position combinations. This is not a complete effective-dated roster or Type 2 player history.

- The team dimension plays team and opponent roles. NFL season/week is a business calendar; no game dates, venues, or home/away labels are fabricated.

- Counts and yards add across compatible observations within one snapshot. Negative yards remain valid. Do not add passing and receiving yards as a combined total.

- Rates use summed numerators and denominators; zero denominators remain NULL. Observed weeks count rows, not roster-confirmed games played.

- Team codes and player profiles are source-derived dimensions. No separate enriched team or player reference datasets are currently loaded. REG and allowed positions are validated contract codes, not separately persisted reference tables.


See [all table and view columns](data-dictionary.md), [worked rows](sample-walkthrough.md), and [the detailed model](model.svg).