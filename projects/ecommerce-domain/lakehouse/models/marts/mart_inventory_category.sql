select coalesce(nullif(trim(category), ''), 'Unknown') as category,
       count(*) as inventory_skus,
       sum(case when stock = 0 then 1 else 0 end) as zero_stock_skus,
       round(100.0 * sum(case when stock = 0 then 1 else 0 end) / nullif(count(*), 0), 2) as zero_stock_share_pct,
       sum(stock) as recorded_stock_units
from {{ ref('stg_inventory') }}
group by 1
