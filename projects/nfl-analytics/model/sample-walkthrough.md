# NFL: source rows become related tables

This compact example selects actual observations from the reviewed 2025 snapshot: one player observed with multiple teams, plus one quarterback. It loads only this subset into a fresh example model; its new hash and row counts describe the subset, not the full 6,037-row snapshot. Raw and normalized source snapshots are kept locally. Original source attribution in NOTICE.md applies.

Generated keys below belong to a fresh example database; use business IDs rather than assuming these surrogate values are portable. UTC load timestamps vary.


## Source: Selected normalized player-week rows

| player_id | player_display_name | position | season | week | season_type | game_id | team | opponent_team | completions | attempts | passing_tds | passing_interceptions | carries | rushing_tds | targets | receptions | receiving_tds | passing_yards | rushing_yards | receiving_yards |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00-0023459 | Aaron Rodgers | QB | 2025 | 1 | REG | 2025_01_PIT_NYJ | PIT | NYJ | 22 | 30 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 244 | -1 | 0 |
| 00-0026158 | Joe Flacco | QB | 2025 | 1 | REG | 2025_01_CIN_CLE | CLE | CIN | 31 | 45 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 290 | 6 | 0 |
| 00-0026158 | Joe Flacco | QB | 2025 | 6 | REG | 2025_06_CIN_GB | CIN | GB | 29 | 45 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 219 | 0 | 0 |


## dim_player

| player_key | player_id |
| --- | --- |
| 1 | 00-0023459 |
| 2 | 00-0026158 |


## dim_player_profile

| profile_key | player_key | player_display_name | position |
| --- | --- | --- | --- |
| 1 | 1 | Aaron Rodgers | QB |
| 2 | 2 | Joe Flacco | QB |


## dim_team

| team_key | team_code |
| --- | --- |
| 1 | CIN |
| 2 | CLE |
| 3 | GB |
| 4 | NYJ |
| 5 | PIT |


## dim_season_week

| week_key | season | season_type | week |
| --- | --- | --- | --- |
| 1 | 2025 | REG | 1 |
| 2 | 2025 | REG | 6 |


## model_snapshot

| snapshot_key | canonical_sha256 | first_payload_sha256 | accepted_rows | loaded_at_utc |
| --- | --- | --- | --- | --- |
| 1 | db6829f905710e2a2b53ef53805458db9efeb8df81aec69ed025a2c808716cb2 | 39155b648c5cbb59ba16bf80ea906a0302c48da731d83e84a45c57b428c62cde | 3 | 2026-11-12T19:31:46.535479+00:00 |


## fact_player_week

| snapshot_key | week_key | player_key | profile_key | team_key | opponent_team_key | game_id | completions | attempts | passing_tds | passing_interceptions | carries | rushing_tds | targets | receptions | receiving_tds | passing_yards | rushing_yards | receiving_yards |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 1 | 1 | 5 | 4 | 2025_01_PIT_NYJ | 22 | 30 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 244 | -1 | 0 |
| 1 | 1 | 2 | 2 | 2 | 1 | 2025_01_CIN_CLE | 31 | 45 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 290 | 6 | 0 |
| 1 | 2 | 2 | 2 | 1 | 3 | 2025_06_CIN_GB | 29 | 45 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 219 | 0 | 0 |


## Trace the results

The same stable player_key occurs with different team_key values on different weekly facts. The team dimension is reused in the opponent role. The original source measures remain on the weekly fact; names and positions resolve through observed profiles. No player is duplicated merely because team membership changes.
