with quotes as (
 select s.price_sheet_row_id, s.source_code, u.metric, trim(u.raw_value) as raw_value
 from {{ ref('stg_price_sheet') }} s,
 lateral (values
  (case when s.source_code='price_may_2022' then 'TP' else 'TP 1' end, s.tp1),
  ('TP 2',s.tp2), ('MRP Old',s."MRP Old"), ('Final MRP Old',s."Final MRP Old"),
  ('Ajio MRP',s."Ajio MRP"), ('Amazon MRP',s."Amazon MRP"), ('Amazon FBA MRP',s."Amazon FBA MRP"),
  ('Flipkart MRP',s."Flipkart MRP"), ('Limeroad MRP',s."Limeroad MRP"), ('Myntra MRP',s."Myntra MRP"),
  ('Paytm MRP',s."Paytm MRP"), ('Snapdeal MRP',s."Snapdeal MRP")
 ) u(metric,raw_value)
 where not (s.source_code='price_may_2022' and u.metric='TP 2')
), parsed as (
 select *, try_cast(replace(raw_value,',','') as decimal(20,2)) as amount,
 try_cast(replace(raw_value,',','') as decimal(24,6)) as precise
 from quotes
)
select r.entity_id as price_quote_id, p.price_sheet_row_id, p.metric, p.raw_value,
 case when p.amount is not null and p.amount=p.precise then cast(p.amount*100 as bigint) end as amount_minor,
 case when coalesce(p.raw_value,'')='' then 'blank' when p.amount is not null and p.amount=p.precise then 'parsed' else 'unparsed' end as value_status,
 cast(null as varchar) as currency
from parsed p join {{ source('raw','raw_quote_registry') }} r on p.price_sheet_row_id=r.price_sheet_row_id and p.metric=r.metric
