"""Replace constant-folded 1/0 checks with data-dependent assertions."""
from pathlib import Path

p = Path("dags/retail_daily.py")
t = p.read_text()

old = """SELECT CASE WHEN COUNT(*) = 0 THEN 1/0 ELSE COUNT(*) END AS fact_rows
            FROM analytics.fact_sales;
            SELECT CASE WHEN COUNT(*) > 0 THEN 1/0 ELSE 0 END AS null_keys
            FROM analytics.fact_sales
            WHERE customer_id IS NULL OR product_id IS NULL OR order_date IS NULL;"""

new = """SELECT 1 / COUNT(*) AS nonzero_fact_check FROM analytics.fact_sales;
            SELECT CAST('null keys found in fact_sales' AS INT)
            FROM analytics.fact_sales
            WHERE customer_id IS NULL OR product_id IS NULL OR order_date IS NULL
            LIMIT 1;"""

assert old in t, "pattern not found"
p.write_text(t.replace(old, new))
print("checks fixed")
