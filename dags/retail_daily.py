"""Daily retail pipeline: S3 bronze -> Redshift staging -> dbt star schema."""
from datetime import datetime, timedelta
from kubernetes.client import models as k8s


from airflow import DAG
from airflow.hooks.base import BaseHook
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook

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
    sql="CREATE SCHEMA IF NOT EXISTS staging; CREATE SCHEMA IF NOT EXISTS analytics;",
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

    dbt_repo_volume = k8s.V1Volume(
        name="dbt-repo", empty_dir=k8s.V1EmptyDirVolumeSource()
    )
    dbt_repo_mount = k8s.V1VolumeMount(name="dbt-repo", mount_path="/dbt-repo")

    dbt_build = KubernetesPodOperator(
    task_id="dbt_build",
    namespace="airflow",
    image="ghcr.io/dbt-labs/dbt-redshift:1.9.latest",
    init_containers=[
        k8s.V1Container(
            name="git-clone",
            image="alpine/git:latest",
            command=["git", "clone", "--depth", "1",
                     "https://github.com/aescal-st/retail-analytics-platform.git",
                     "/dbt-repo"],
            volume_mounts=[dbt_repo_mount],
        )
    ],
    cmds=["dbt", "build",
          "--project-dir", "/dbt-repo/dbt",
          "--profiles-dir", "/dbt-repo/dbt"],
    env_vars={
        "REDSHIFT_HOST": _rs.host,
        "REDSHIFT_USER": _rs.login,
        "REDSHIFT_PASSWORD": _rs.password or "",
        "REDSHIFT_DBNAME": _rs.schema or "retail",
    },
    volumes=[dbt_repo_volume],
    volume_mounts=[dbt_repo_mount],
    get_logs=True,
    is_delete_operator_pod=True,
    )


    @task
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
        print(f"data quality passed: {fact_rows} fact rows, 0 null keys")

    create_schemas >> create_staging_tables >> copy_bronze_to_staging >> dbt_build >> data_quality_checks()
