select customer_id, first_name, last_name, email, city, state,
       signup_date::date as signup_date
from {{ source('raw', 'raw_customers') }}
