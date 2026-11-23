select r.entity_id as warehouse_row_id, a._source_row as source_row,
 a."Shiprocket" as shiprocket_label, a."Unnamed: 1" as middle_text, a."INCREFF" as increff_text
from {{ source('raw','raw_warehouse_comparison') }} a
join {{ source('raw','raw_entity_current') }} r on r.entity = 'warehouse_comparison' and r.source_row = a._source_row
