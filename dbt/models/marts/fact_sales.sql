select order_id, customer_id, product_id, order_date,
       quantity, unit_price, line_total
from {{ ref('stg_orders') }}
where status = 'completed'
