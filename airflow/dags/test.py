from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
import pendulum

with DAG(
    dag_id="test_pod_permissions",
    schedule=None,          # déclenché à la main
    start_date=pendulum.datetime(2026, 8, 1, tz="Europe/Paris"),
    catchup=False,
) as dag:
    KubernetesPodOperator(
        task_id="hello",
        name="hello-pod",
        image="busybox",
        cmds=["sh", "-c", "echo ok"],
    )