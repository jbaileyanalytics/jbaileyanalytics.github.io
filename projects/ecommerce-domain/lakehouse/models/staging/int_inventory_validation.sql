with cleaned as (
 select *, upper(trim("SKU Code")) as sku_normalized,
 try_cast(trim("Stock") as double) as stock_parsed,
 count(*) over (partition by upper(trim("SKU Code"))) as sku_count
 from {{ source('raw', 'raw_inventory') }}
)
select *, case when sku_normalized = '' then 'missing SKU'
 when sku_count > 1 then 'ambiguous duplicate SKU'
 when stock_parsed is null or not isfinite(stock_parsed) or stock_parsed < 0 then 'invalid stock'
 else null end as rejection_reason
from cleaned
