# Data attribution

Source: nflverse contributors, [nflverse-data](https://github.com/nflverse/nflverse-data), [Player Summary Stats release](https://github.com/nflverse/nflverse-data/releases/tag/stats_player).

The upstream repository publishes a [Creative Commons Attribution 4.0 International license](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md). License text and terms: https://creativecommons.org/licenses/by/4.0/ . No endorsement by nflverse or the NFL is implied.

Source URL, HTTP Last-Modified, retrieval timestamp, original SHA-256, normalized SHA-256, and quality counts are recorded in local ingestion manifests, which are excluded from Git. The published season index contains the source URL, retrieval timestamp, and normalized hash.

Modifications: retained regular-season QB/RB/WR/TE records, selected documented columns, trimmed identifiers, validated integer statistics and keys, sorted player-week records, and converted to normalized CSV and week-partitioned Parquet. Dashboard metrics and charts are derived from these transformed records and user-selected filters. Source headshots and logos are not included.
