from datetime import datetime

from airflow.sdk import DAG, task


with DAG(
    dag_id="hello_airflow",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    @task
    def hello():
        print("Hello from Airflow!")

    hello()