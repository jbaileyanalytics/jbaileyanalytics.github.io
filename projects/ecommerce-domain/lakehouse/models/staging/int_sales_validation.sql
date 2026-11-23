with cleaned as (
 select *, upper(trim("SKU")) as sku_normalized,
 try_strptime(trim("Date"), '%m-%d-%y')::date as sale_date,
 try_cast(trim("Qty") as integer) as qty_parsed,
 try_cast(nullif(trim("Amount"), '') as decimal(18,2)) as amount_parsed,
 try_cast(nullif(trim("Amount"), '') as decimal(24,6)) as amount_precision,
 lower(trim("B2B")) as b2b_normalized,
 count(*) over (partition by "index") as source_index_count
 from {{ source('raw', 'raw_amazon') }}
)
select *, case
 when trim("Order ID") = '' or sku_normalized = '' then 'missing order or SKU'
 when try_cast("index" as bigint) is null or source_index_count > 1 then 'invalid or duplicate source index'
 when sale_date is null then 'invalid date'
 when qty_parsed is null then 'invalid quantity'
 when trim("Amount") <> '' and (amount_parsed is null or amount_precision is null or amount_parsed <> amount_precision) then 'invalid amount'
 when b2b_normalized not in ('true','false','') then 'invalid B2B'
 else null end as rejection_reason
from cleaned
