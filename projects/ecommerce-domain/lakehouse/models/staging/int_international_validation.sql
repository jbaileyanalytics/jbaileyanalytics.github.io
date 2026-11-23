with parsed as (
 select *, try_strptime(trim("DATE"), '%m-%d-%y')::date as sale_date,
 try_cast(replace(trim("PCS"), ',', '') as decimal(20,4)) as quantity_value,
 try_cast(replace(trim("RATE"), ',', '') as decimal(20,2)) as rate_value,
 try_cast(replace(trim("GROSS AMT"), ',', '') as decimal(20,2)) as gross_value,
 try_cast(replace(trim("RATE"), ',', '') as decimal(24,6)) as rate_raw,
 try_cast(replace(trim("GROSS AMT"), ',', '') as decimal(24,6)) as gross_raw
 from {{ source('raw','raw_international') }}
)
select *, case when sale_date is null or quantity_value is null or quantity_value < 0 or rate_value is null or gross_value is null or rate_value <> rate_raw or gross_value <> gross_raw then 'invalid date or transaction measure' else null end as rejection_reason
from parsed
