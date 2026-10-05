"""Replace SQL quality check with Python assertions."""
from pathlib import Path

p = Path("dags/retail_daily.py")
t = p.read_text()

old_imp = "from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator"
new_imp = old_imp + "\nfrom airflow.decorators import task\nfrom airflow.providers.postgres.hooks.postgres import PostgresHook"
assert old_imp in t, "import anchor not found"
t = t.replace(old_imp, new_imp)

old_task = '''    data_quality_checks = SQLExecuteQueryOperator(
        task_id="data_quality_checks",
        conn_id=REDSHIFT_CONN_ID,
        sql="""
            SELECT 1 / COUNT(*) AS nonzero_fact_check FROM analytics.fact_sales;
            SELECT CAST('null keys found in fact_sales' AS INT)
            FROM analytics.fact_sales
            WHERE customer_id IS NULL OR product_id IS NULL OR order_date IS NULL
            LIMIT 1;
        """,
    )'''
new_task = '''    @task
    def data_quality_checks():
        """Fail loudly if marts are empty or have null keys."""
        hook = PostgresHook(postgres_conn_id=REDSHIFT_CONN_ID)
        fact_rows = hook.get_first("SELECT COUNT(*) FROM analytics.fact_sales")[0]
        assert fact_rows > 0, "fact_sales is empty"
        null_keys = hook.get_first(
            "SELECT COUNT(*) FROM analytics.fact_sales "
            "WHERE customer_id IS NULL OR product_id IS NULL OR order_date IS NULL"
        )[0]
        assert null_keys == 0, f"{null_keys} null keys in fact_sales"
        print(f"data quality passed: {fact_rows} fact rows, 0 null keys")'''
assert old_task in t, "task block not found"
t = t.replace(old_task, new_task)

old_chain = ">> dbt_build >> data_quality_checks"
new_chain = ">> dbt_build >> data_quality_checks()"
assert old_chain in t, "chain not found"
t = t.replace(old_chain, new_chain)

p.write_text(t)
print("rewritten")
