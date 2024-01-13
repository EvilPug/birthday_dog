from __future__ import annotations

# [START tutorial]
# [START import_module]
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from src import partycleaner

# [END import_module]


# [START instantiate_dag]
with DAG(
        "birthday",
        # [START default_args]
        default_args={
            "depends_on_past": False,
            "email": ["airflow@example.com"],
            "email_on_failure": False,
            "email_on_retry": False,
            "retries": 1,
            "retry_delay": timedelta(minutes=5),
        },
        # [END default_args]
        description="A simple tutorial DAG",
        schedule=timedelta(days=1),
        start_date=datetime(2021, 1, 1),
        catchup=False,
        tags=["example"],
) as dag:
    # [END instantiate_dag]

    # [START birthday_tasks]
    t1 = PythonOperator(dag=dag,
                        task_id='clean_party',
                        provide_context=False,
                        python_callable=main,
                        op_args=['arguments_passed_to_callable'],
                        op_kwargs={'keyword_argument': 'which will be passed to function'})

    t2 = BashOperator(
        task_id="make_party",
        depends_on_past=False,
        bash_command="python -m partymaker.py",
    )
    # [END birthday_tasks]

    t1 >> t2
# [END birthday]
