# Orchestration Airflow

Un DAG, `velib_pipeline`, lance toutes les 15 minutes cinq pods Kubernetes en
séquence à partir des images publiées sur ghcr.io.

```
ingest_velib ──┐
               ├──> dbt_freshness ──> dbt_run ──> dbt_test
ingest_meteo ──┘
```

Airflow n'embarque aucune dépendance métier. Il connaît les noms des images et
les commandes à lancer, rien d'autre. Le code d'ingestion et le projet dbt
vivent dans leurs propres images.

## Fichiers

| Fichier | Rôle |
|---|---|
| `dags/velib_pipeline.py` | Le DAG de production |

## Comment le DAG arrive dans Airflow

L'Airflow du catalogue Onyxia synchronise ce dossier depuis GitHub via git-sync.
Repository `https://github.com/surybang/Velib.git`, sous-chemin `airflow/dags`,
branche `main`. Un push sur main suffit, le DAG apparaît dans l'UI en une minute.

## Paramètres notables

`schedule="*/15 * * * *"` est calé sur le rafraîchissement du cache de l'API
Vélib'. Fetcher plus souvent produirait des doublons rejetés par la contrainte
d'unicité.

`catchup=False` parce que l'API n'expose que l'état courant. Les runs manqués
ne sont pas rattrapables.

`max_active_runs=1` pour éviter que deux `dbt run` se chevauchent sur la même
table gold.

`retries=2` avec `retry_delay` de 2 minutes. Suffisant pour absorber une API
qui répond 503 ponctuellement, sans masquer un vrai problème.

## Prérequis Kubernetes

Le PodOperator a besoin que le worker Airflow puisse créer des pods. Sur le
catalogue Onyxia ce n'est pas le cas par défaut. La procédure complète est dans
`deploy/sspcloud/README.md`.
