select r.entity_id as sales_line_id,
 p.product_id, s._source_row as source_row, trim(s."Order ID") as source_order_id,
 s.sale_date as calendar_date, p.sku, trim(s."Style") as style, trim(s."Category") as category,
 trim(s."Size") as size, trim(s."Status") as status, trim(s."Fulfilment") as fulfillment,
 trim(s."Sales Channel ") as sales_channel, s.qty_parsed as quantity,
 nullif(trim(s."currency"), '') as currency, cast(s.amount_parsed * 100 as bigint) as amount_minor,
 case s.b2b_normalized when 'true' then 1 when 'false' then 0 else null end as b2b
from {{ ref('int_sales_validation') }} s join {{ ref('dim_product') }} p on s.sku_normalized = p.sku
join {{ source('raw','raw_entity_current') }} r on r.entity = 'amazon' and r.source_row = s._source_row
where s.rejection_reason is null
