# NFL player performance: complete table dictionary

Generated from the implemented SQLite schema. PK = primary key; FK = foreign key; UQ = alternate unique key. Nullable follows the model contract, with PK columns treated as required. SQLite TEXT stores ISO dates, timestamps, or exact decimal strings where specified. Expressions in reporting views may have no declared SQLite type.


## dim_player

Grain: One stable source player ID.

| Column | Physical type | Nullable | Keys / relationship |
| --- | --- | --- | --- |
| player_key | INTEGER | No | PK |
| player_id | TEXT | No | UQ |


Primary key: `(player_key)`.

Unique constraints: `(player_id)`.


## dim_player_profile

Grain: One player + reported name + position.

| Column | Physical type | Nullable | Keys / relationship |
| --- | --- | --- | --- |
| profile_key | INTEGER | No | PK |
| player_key | INTEGER | No | FK → dim_player.player_key |
| player_display_name | TEXT | No | — |
| position | TEXT | No | — |


Primary key: `(profile_key)`.

Unique constraints: `(profile_key, player_key)`; `(player_key, player_display_name, position)`.


## dim_team

Grain: One source team code.

| Column | Physical type | Nullable | Keys / relationship |
| --- | --- | --- | --- |
| team_key | INTEGER | No | PK |
| team_code | TEXT | No | UQ |


Primary key: `(team_key)`.

Unique constraints: `(team_code)`.


## dim_season_week

Grain: One season + season type + week.

| Column | Physical type | Nullable | Keys / relationship |
| --- | --- | --- | --- |
| week_key | INTEGER | No | PK |
| season | INTEGER | No | — |
| season_type | TEXT | No | — |
| week | INTEGER | No | — |


Primary key: `(week_key)`.

Unique constraints: `(season, season_type, week)`.


## model_snapshot

Grain: One canonical accepted source revision.

| Column | Physical type | Nullable | Keys / relationship |
| --- | --- | --- | --- |
| snapshot_key | INTEGER | No | PK |
| canonical_sha256 | TEXT | No | UQ |
| first_payload_sha256 | TEXT | No | — |
| accepted_rows | INTEGER | No | — |
| loaded_at_utc | TEXT | No | — |


Primary key: `(snapshot_key)`.

Unique constraints: `(canonical_sha256)`.


## fact_player_week

Grain: One player + season/type/week per snapshot.

| Column | Physical type | Nullable | Keys / relationship |
| --- | --- | --- | --- |
| snapshot_key | INTEGER | No | PK; FK → model_snapshot.snapshot_key |
| week_key | INTEGER | No | PK; FK → dim_season_week.week_key |
| player_key | INTEGER | No | PK; FK → dim_player_profile.player_key; FK → dim_player.player_key |
| profile_key | INTEGER | No | FK → dim_player_profile.profile_key |
| team_key | INTEGER | No | FK → dim_team.team_key |
| opponent_team_key | INTEGER | No | FK → dim_team.team_key |
| game_id | TEXT | No | — |
| completions | INTEGER | No | — |
| attempts | INTEGER | No | — |
| passing_tds | INTEGER | No | — |
| passing_interceptions | INTEGER | No | — |
| carries | INTEGER | No | — |
| rushing_tds | INTEGER | No | — |
| targets | INTEGER | No | — |
| receptions | INTEGER | No | — |
| receiving_tds | INTEGER | No | — |
| passing_yards | INTEGER | No | — |
| rushing_yards | INTEGER | No | — |
| receiving_yards | INTEGER | No | — |


Primary key: `(snapshot_key, week_key, player_key)`.

Unique constraints: `(snapshot_key, week_key, player_key)`.


## Relationship register

Each row describes child → parent columns. Composite relationships must be enforced together.

| Child columns | Parent columns | Parents per child | Children per parent |
| --- | --- | --- | --- |
| dim_player_profile (player_key) | dim_player (player_key) | 1 | 0..many |
| fact_player_week (profile_key, player_key) | dim_player_profile (profile_key, player_key) | 1 | 0..many |
| fact_player_week (opponent_team_key) | dim_team (team_key) | 1 | 0..many |
| fact_player_week (team_key) | dim_team (team_key) | 1 | 0..many |
| fact_player_week (player_key) | dim_player (player_key) | 1 | 0..many |
| fact_player_week (week_key) | dim_season_week (week_key) | 1 | 0..many |
| fact_player_week (snapshot_key) | model_snapshot (snapshot_key) | 1 | 0..many |


## Reporting view: v_player_season_totals

| Output column | Declared SQLite type |
| --- | --- |
| snapshot_key | INTEGER |
| season | INTEGER |
| season_type | TEXT |
| player_id | TEXT |
| observed_weeks | Derived expression (see SQL) |
| attempts | Derived expression (see SQL) |
| passing_yards | Derived expression (see SQL) |
| carries | Derived expression (see SQL) |
| rushing_yards | Derived expression (see SQL) |
| targets | Derived expression (see SQL) |
| receiving_yards | Derived expression (see SQL) |
| yards_per_attempt | Derived expression (see SQL) |
| yards_per_carry | Derived expression (see SQL) |
| yards_per_target | Derived expression (see SQL) |
| catch_rate | Derived expression (see SQL) |


## Reporting view: v_player_week

| Output column | Declared SQLite type |
| --- | --- |
| snapshot_key | INTEGER |
| player_id | TEXT |
| player_display_name | TEXT |
| position | TEXT |
| season | INTEGER |
| week | INTEGER |
| season_type | TEXT |
| game_id | TEXT |
| team | TEXT |
| opponent_team | TEXT |
| completions | INTEGER |
| attempts | INTEGER |
| passing_tds | INTEGER |
| passing_interceptions | INTEGER |
| carries | INTEGER |
| rushing_tds | INTEGER |
| targets | INTEGER |
| receptions | INTEGER |
| receiving_tds | INTEGER |
| passing_yards | INTEGER |
| rushing_yards | INTEGER |
| receiving_yards | INTEGER |


## Interpretation and constraints

- The input is already at player-week grain. Modeling separates repeating identities and observed attributes while retaining source measures on one weekly fact.

- The player dimension uses stable IDs, not names. A trade changes the fact's team key; it does not change player identity or rewrite earlier team production.

- Player profiles preserve observed name/position combinations. This is not a complete effective-dated roster or Type 2 player history.

- The team dimension plays team and opponent roles. NFL season/week is a business calendar; no game dates, venues, or home/away labels are fabricated.

- Counts and yards add across compatible observations within one snapshot. Negative yards remain valid. Do not add passing and receiving yards as a combined total.

- Rates use summed numerators and denominators; zero denominators remain NULL. Observed weeks count rows, not roster-confirmed games played.

- Team codes and player profiles are source-derived dimensions. No separate enriched team or player reference datasets are currently loaded. REG and allowed positions are validated contract codes, not separately persisted reference tables.
