-- Every source price row must produce the expected number of distinct metrics.
select s.price_sheet_row_id, s.source_code, count(q.price_quote_id) as actual
from {{ ref('stg_price_sheet') }} s
left join {{ ref('fact_price_quote') }} q on s.price_sheet_row_id=q.price_sheet_row_id
group by s.price_sheet_row_id, s.source_code
having count(q.price_quote_id) <> case when s.source_code='price_may_2022' then 11 else 12 end
    or count(distinct q.metric) <> case when s.source_code='price_may_2022' then 11 else 12 end
