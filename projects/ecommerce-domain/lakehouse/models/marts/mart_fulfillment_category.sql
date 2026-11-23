select coalesce(nullif(trim(fulfillment), ''), 'Unknown') as fulfillment,
       coalesce(nullif(trim(category), ''), 'Unknown') as category,
       count(*) as sales_lines,
       sum(case when status = 'Cancelled' then 1 else 0 end) as cancelled_lines,
       round(100.0 * sum(case when status = 'Cancelled' then 1 else 0 end) / nullif(count(*), 0), 2) as cancellation_rate_pct
from {{ ref('stg_sales_lines') }}
group by 1, 2
