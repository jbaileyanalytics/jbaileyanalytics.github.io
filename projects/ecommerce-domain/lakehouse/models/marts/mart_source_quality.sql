with counts as (
 select 'amazon' as source_code, count(*) filter (where rejection_reason is null) as accepted_rows, count(*) filter (where rejection_reason is not null) as rejected_rows from {{ ref('int_sales_validation') }}
 union all select 'inventory', count(*) filter (where rejection_reason is null), count(*) filter (where rejection_reason is not null) from {{ ref('int_inventory_validation') }}
 union all select 'international', count(*) filter (where rejection_reason is null), count(*) filter (where rejection_reason is not null) from {{ ref('int_international_validation') }}
 union all select source_code, count(*), 0 from {{ ref('stg_price_sheet') }} group by 1
 union all select 'expense_iigf', count(*), 0 from {{ ref('stg_expense_rows') }}
 union all select 'warehouse_comparison', count(*), 0 from {{ ref('stg_warehouse_rows') }}
)
select f.source_code, f.row_count as source_rows, coalesce(c.accepted_rows,0) as accepted_rows,
 coalesce(c.rejected_rows,0) as rejected_rows, f.row_count-coalesce(c.accepted_rows,0)-coalesce(c.rejected_rows,0) as unreconciled_rows,
 case when f.source_code in ('amazon','inventory','international') then 'validated' else 'retained_source_rows' end as processing_status
from {{ source('raw','raw_source_manifest') }} f left join counts c using (source_code)
