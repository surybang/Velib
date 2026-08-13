"""DAG d'orchestration du pipeline Vélib'.

Chaque tâche lance un pod à partir d'une image publiée sur le registre.

Chaîne : collectes (en parallèle) -> dbt run -> dbt test
"""

from pathlib import Path

import pendulum
from airflow.models.dag import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s


def _current_namespace() -> str:
    """Namespace du pod Airflow courant, injecté par Kubernetes."""
    token_path = Path(
        "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    )
    if token_path.exists():
        return token_path.read_text().strip()
    return "default"


NAMESPACE = _current_namespace()
REGISTRY = "ghcr.io/surybang"
IMAGE_TAG = "latest"

# Identifiants et configuration injectés depuis Kubernetes, jamais depuis le code.
ENV_FROM = [
    k8s.V1EnvFromSource(
        secret_ref=k8s.V1SecretEnvSource(name="velib-postgres-credentials")
    ),
    k8s.V1EnvFromSource(config_map_ref=k8s.V1ConfigMapEnvSource(name="velib-config")),
]

DEFAULT_ARGS = {
    "owner": "data",
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=2),
    "execution_timeout": pendulum.duration(minutes=10),
}


def pod_task(task_id: str, image: str, arguments: list[str]) -> KubernetesPodOperator:
    """Fabrique une tâche pod avec la configuration commune du projet."""
    return KubernetesPodOperator(
        task_id=task_id,
        name=task_id.replace("_", "-"),
        namespace=NAMESPACE,
        image=f"{REGISTRY}/{image}:{IMAGE_TAG}",
        cmds=arguments,
        env_from=ENV_FROM,
        get_logs=True,
        in_cluster=True,
        # Le pod est supprimé après coup ; les logs sont déjà remontés dans Airflow.
        on_finish_action="delete_pod",
        # Un exit code non nul du pod fait échouer la tâche Airflow.
        startup_timeout_seconds=300,
    )


with DAG(
    dag_id="velib_pipeline",
    description="Collecte Vélib' + météo, puis transformation dbt",
    # Cadence calée sur le rafraîchissement réel du cache de l'API (~15 min).
    # Fetcher plus souvent ne produirait que des doublons.
    schedule="*/15 * * * *",
    start_date=pendulum.datetime(2026, 8, 1, tz="Europe/Paris"),
    # Pas de rattrapage : l'API n'expose que l'état courant, les snapshots
    # passés ne sont pas récupérables.
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["velib", "ingestion", "dbt"],
) as dag:
    ingest_velib = pod_task("ingest_velib", "velib-ingestion", ["ingest-velib"])
    ingest_meteo = pod_task("ingest_meteo", "velib-ingestion", ["ingest-meteo"])

    dbt_run = pod_task("dbt_run", "velib-dbt", ["dbt", "run"])
    dbt_test = pod_task("dbt_test", "velib-dbt", ["dbt", "test"])

    # Collectes indépendantes en parallèle ; dbt ne démarre que si les deux
    # ont réussi ; les tests suivent le run.
    [ingest_velib, ingest_meteo] >> dbt_run >> dbt_test
