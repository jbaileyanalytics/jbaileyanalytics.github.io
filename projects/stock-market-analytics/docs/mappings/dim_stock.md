# Stock reference mapping

Grain: one observed ticker in the current source universe. Primary key: `stock_id`.

| Target | Source | Rule |
| --- | --- | --- |
| stock_id | ticker | Assign an auto-incrementing surrogate ID in the initial database. The database must be retained; incremental ID reuse is not implemented. |
| ticker | `ticker` and filename | Require exact agreement with the filename; a mismatch stops the build. |

Uniqueness is provisional to this dataset. A ticker is not a verified permanent security identifier. Company name, sector, and exchange history are not present in the sampled source and must not be invented.
