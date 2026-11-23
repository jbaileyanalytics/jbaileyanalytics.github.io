select s.sales_line_id from {{ ref('stg_sales_lines') }} s
left join {{ ref('dim_product') }} p on s.product_id = p.product_id
where p.product_id is null
