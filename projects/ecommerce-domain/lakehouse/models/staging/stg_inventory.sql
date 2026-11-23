select r.entity_id as inventory_snapshot_id, p.product_id,
 i._source_row as source_row, p.sku, i.stock_parsed as stock,
 trim(i."Category") as category, trim(i."Size") as size, trim(i."Color") as color,
 cast(null as date) as snapshot_date
from {{ ref('int_inventory_validation') }} i join {{ ref('dim_product') }} p on i.sku_normalized=p.sku
join {{ source('raw','raw_entity_current') }} r on r.entity = 'inventory' and r.source_row = i._source_row
where i.rejection_reason is null
