select sku_normalized as sku from {{ ref('int_sales_validation') }} where rejection_reason is null
union select sku_normalized as sku from {{ ref('int_inventory_validation') }} where rejection_reason is null
union select upper(trim("SKU")) as sku from {{ ref('int_international_validation') }} where rejection_reason is null and trim("SKU") <> ''
union select upper(trim(sku)) as sku from {{ ref('stg_price_sheet') }} where sku is not null
