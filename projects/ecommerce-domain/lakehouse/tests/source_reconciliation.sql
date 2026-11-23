select * from {{ ref('mart_source_quality') }} where unreconciled_rows <> 0
