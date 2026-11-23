select r.entity_id as expense_row_id, a._source_row as source_row, a."Recived Amount" as received_description,
 a."Unnamed: 1" as received_amount_raw, a."Expance" as expense_description, a."Unnamed: 3" as expense_amount_raw
from {{ source('raw','raw_expense_iigf') }} a
join {{ source('raw','raw_entity_current') }} r on r.entity = 'expense_iigf' and r.source_row = a._source_row
