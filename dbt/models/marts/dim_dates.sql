select distinct
    order_date as date_day,
    extract(year from order_date)::int as year,
    extract(month from order_date)::int as month,
    extract(day from order_date)::int as day,
    to_char(order_date, 'Day') as day_name
from {{ ref('stg_orders') }}
