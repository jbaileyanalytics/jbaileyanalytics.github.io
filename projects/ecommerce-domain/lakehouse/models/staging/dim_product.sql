select r.product_id, r.sku from {{ source('raw', 'raw_product_registry') }} r join {{ ref('int_sku_set') }} s on r.sku = s.sku
