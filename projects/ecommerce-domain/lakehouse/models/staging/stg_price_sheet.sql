with rows as (
 select 'price_may_2022' as source_code, * exclude ("TP"), "TP" as tp1, cast(null as varchar) as tp2 from {{ source('raw','raw_price_may_2022') }}
 union all by name
 select 'price_march_2021' as source_code, * exclude ("TP 1", "TP 2"), "TP 1" as tp1, "TP 2" as tp2 from {{ source('raw','raw_price_march_2021') }}
)
select r.entity_id as price_sheet_row_id, a.source_code, a._source_row as source_row,
 p.product_id, nullif(upper(trim(a."Sku")), '') as sku, trim(a."Style Id") as style,
 trim(a."Catalog") as catalog, trim(a."Category") as category, a."Weight" as weight_raw,
 a.tp1, a.tp2, a."MRP Old", a."Final MRP Old", a."Ajio MRP", a."Amazon MRP", a."Amazon FBA MRP",
 a."Flipkart MRP", a."Limeroad MRP", a."Myntra MRP", a."Paytm MRP", a."Snapdeal MRP"
from rows a
join {{ source('raw','raw_entity_current') }} r on r.entity = a.source_code and r.source_row = a._source_row
left join {{ source('raw','raw_product_registry') }} p on p.sku=upper(trim(a."Sku"))
