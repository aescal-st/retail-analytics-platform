"""Daily retail pipeline: S3 bronze -> Redshift staging -> dbt star schema."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.hooks.base import BaseHook
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

REDSHIFT_CONN_ID = "redshift_default"
BUCKET = "retail-analytics-lake-495249387077"
REDSHIFT_S3_ROLE = "arn:aws:iam::495249387077:role/retail-analytics-redshift-s3"

# Resolved at DAG-parse time: create the `redshift_default` connection in the
# Airflow UI before triggering (the import error clears itself once it exists).
_rs = BaseHook.get_connection(REDSHIFT_CONN_ID)

default_args = {"owner": "data-eng", "retries": 1, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="retail_daily",
    description="Bronze CSVs -> Redshift staging -> dbt star schema",
    schedule="@daily",
    start_date=datetime(2026, 10, 4),
    catchup=False,
    default_args=default_args,
    tags=["retail", "redshift", "dbt"],
) as dag:

    create_schemas = SQLExecuteQueryOperator(
        task_id="create_schemas",
        conn_id=REDSHIFT_CONN_ID,
        sql="CREATE SCHEMA IF NOT EXISTS raw; CREATE SCHEMA IF NOT EXISTS analytics;",
    )

    create_staging_tables = SQLExecuteQueryOperator(
        task_id="create_staging_tables",
        conn_id=REDSHIFT_CONN_ID,
        sql="""
            CREATE TABLE IF NOT EXISTS staging.raw_orders (
                order_id INT, customer_id INT, product_id INT, quantity INT,
                unit_price DECIMAL(10,2), order_date DATE, status VARCHAR(20));
            CREATE TABLE IF NOT EXISTS staging.raw_customers (
                customer_id INT, first_name VARCHAR(50), last_name VARCHAR(50),
                email VARCHAR(100), city VARCHAR(50), state VARCHAR(10), signup_date DATE);
            CREATE TABLE IF NOT EXISTS staging.raw_products (
                product_id INT, product_name VARCHAR(100),
                category VARCHAR(50), unit_price DECIMAL(10,2));
        """,
    )

    copy_bronze_to_staging = SQLExecuteQueryOperator(
        task_id="copy_bronze_to_staging",
        conn_id=REDSHIFT_CONN_ID,
        sql=f"""
            TRUNCATE staging.raw_orders;
            COPY staging.raw_orders FROM 's3://{BUCKET}/bronze/orders.csv'
            IAM_ROLE '{REDSHIFT_S3_ROLE}' CSV IGNOREHEADER 1;
            TRUNCATE staging.raw_customers;
            COPY staging.raw_customers FROM 's3://{BUCKET}/bronze/customers.csv'
            IAM_ROLE '{REDSHIFT_S3_ROLE}' CSV IGNOREHEADER 1;
            TRUNCATE staging.raw_products;
            COPY staging.raw_products FROM 's3://{BUCKET}/bronze/products.csv'
            IAM_ROLE '{REDSHIFT_S3_ROLE}' CSV IGNOREHEADER 1;
        """,
    )

    dbt_build = KubernetesPodOperator(
        task_id="dbt_build",
        namespace="airflow",
        image="ghcr.io/dbt-labs/dbt-redshift:1.9.latest",
        cmds=["dbt", "build",
              "--project-dir", "/opt/airflow/dags/dbt",
              "--profiles-dir", "/opt/airflow/dags/dbt"],
        env_vars={
            "REDSHIFT_HOST": _rs.host,
            "REDSHIFT_USER": _rs.login,
            "REDSHIFT_PASSWORD": _rs.password or "",
            "REDSHIFT_DBNAME": _rs.schema or "retail",
        },
        get_logs=True,
        is_delete_operator_pod=True,
    )

    data_quality_checks = SQLExecuteQueryOperator(
        task_id="data_quality_checks",
        conn_id=REDSHIFT_CONN_ID,
        sql="""
            SELECT CASE WHEN COUNT(*) = 0 THEN 1/0 ELSE COUNT(*) END AS fact_rows
            FROM analytics.fact_sales;
            SELECT CASE WHEN COUNT(*) > 0 THEN 1/0 ELSE 0 END AS null_keys
            FROM analytics.fact_sales
            WHERE customer_id IS NULL OR product_id IS NULL OR order_date IS NULL;
        """,
    )

    create_schemas >> create_staging_tables >> copy_bronze_to_staging >> dbt_build >> data_quality_checks
