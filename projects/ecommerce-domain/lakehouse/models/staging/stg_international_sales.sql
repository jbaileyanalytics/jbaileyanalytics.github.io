select r.entity_id as international_sale_id, i._source_row as source_row, i.sale_date,
 p.product_id, nullif(upper(trim(i."SKU")), '') as sku,
 trim(i."Style") as style, trim(i."Size") as size, i.quantity_value as quantity,
 cast(i.rate_value * 100 as bigint) as rate_minor, cast(i.gross_value * 100 as bigint) as gross_minor,
 cast(null as varchar) as currency
from {{ ref('int_international_validation') }} i
join {{ source('raw','raw_entity_current') }} r on r.entity = 'international' and r.source_row = i._source_row
left join {{ source('raw','raw_product_registry') }} p on p.sku=upper(trim(i."SKU"))
where i.rejection_reason is null
