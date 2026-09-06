# Vélib' × Météo

Pipeline de données qui collecte l'état des 995 stations Vélib' de Paris et la
météo locale toutes les 15 minutes, les stocke dans PostgreSQL, et les transforme
en une table de faits prête pour l'analyse et la prédiction de disponibilité.

Tourne en production sur SSP Cloud (Onyxia) depuis août 2026, orchestré par Airflow.

## Ce que fait le pipeline

```
API Open Data Paris  ──┐
  (995 stations)       │
                       ├──> ingestion ──> PostgreSQL bronze ──> dbt ──> gold.fct_velib_meteo
API Open-Meteo       ──┘                                        (silver → gold)
  (Paris)

Orchestration : Airflow, KubernetesPodOperator, un pod par tâche
Cadence       : toutes les 15 minutes
```

Chaque run lance quatre pods en séquence : deux collectes en parallèle (Vélib',
météo), puis `dbt run` pour reconstruire la table gold, puis `dbt test` (27 tests).

## Organisation du dépôt

| Dossier | Rôle |
|---|---|
| `ingestion/` | Service Python qui interroge les deux APIs et écrit dans bronze |
| `dbt/` | Modélisation médaillon, 4 modèles, 27 tests |
| `airflow/dags/` | DAG d'orchestration |
| `pgsql/` | Schéma initial de la base |
| `deploy/sspcloud/` | RBAC Kubernetes, secrets, runbook de mise en route |
| `API_Docs/` | Notes sur les deux APIs sources et leurs particularités |

Chaque service a son `pyproject.toml`, son `uv.lock` et son Dockerfile. Ils ne
s'importent pas mutuellement et se déploient séparément.

## Démarrer en local

```bash
cp .env.example .env    # renseigner PGHOST, PGUSER, PGPASSWORD, PGDATABASE
psql "$DATABASE_URL" -f pgsql/01_init.sql

cd ingestion && uv sync && uv run ingest-velib && uv run ingest-meteo
cd ../dbt && uv sync && uv run dbt deps && uv run dbt run && uv run dbt test
```

Qualité de code :

```bash
uv tool install prek && prek install    # ruff + sqlfluff au commit
cd ingestion && uv run pytest           # 16 tests, sans réseau ni base
```

## Ce que la source impose

Trois contraintes découvertes en instrumentant le pipeline, qui conditionnent
ce qu'on peut conclure des données.

**L'endpoint paginé de l'API Vélib' est mis en cache.** Une requête ciblée par
`stationcode` renvoie un `duedate` frais à la seconde. La requête paginée qui
récupère les 995 stations renvoie un snapshot rafraîchi toutes les 15 minutes
environ. Sur les mêmes stations au même instant, l'écart entre les deux a
atteint une heure. La cadence de collecte est donc calée sur ce rythme,
interroger plus souvent ne produit que des doublons.

**`duedate` et `ingested_at` sont deux horloges différentes.** `duedate` vient
de l'API et subit le cache. `ingested_at` est posée par PostgreSQL à l'insertion.
La première sert à la jointure météo et à l'analyse temporelle, la seconde à
surveiller la santé de la collecte. Les confondre a coûté plusieurs heures de
diagnostic, d'où cette note.

**La station 15056 (Place Balard) déclare une capacité de 22** mais accueille
régulièrement plus de 40 vélos. Son taux d'occupation dépassait 190 %. La couche
gold le plafonne à 100.

Vélib' ne publie pas les trajets. Les variations de `bikes_available` entre deux
snapshots donnent un solde net par station, sans distinguer un usage réel d'un
rééquilibrage par camion.

## Diagnostic des trous de collecte

```bash
cd dbt && uv run dbt show --select analyses_gap --limit 20
```

Affiche les pauses de collecte avec leur durée. Avant Airflow, un scheduler
tournait dans une session VSCode et mourait la nuit, d'où des trous systématiques
de 4h à 22h dans l'historique de juillet 2026.

La base PostgreSQL vient aussi du catalogue Onyxia. Si le service tombe, il faut
le relancer à la main, ce qui crée un trou de collecte. La solution propre est de
déployer la base via ArgoCD pour qu'elle soit maintenue automatiquement, comme
Airflow devrait l'être.

## Choix écartés

**Spark.** 95 000 lignes par jour, trois ordres de grandeur sous le seuil où le
calcul distribué se justifie.

**Feature store dédié.** La couche gold dbt est déjà la définition unique,
versionnée et testée des features. Un feature store se justifierait avec plusieurs
consommateurs ou un serving à faible latence.

**Data lake en amont.** Bronze conserve déjà le brut rejouable. Un stockage objet
servira plus tard aux artefacts de modèles, pas aux données sources.

## Suite prévue

Dashboard Streamlit avec API FastAPI, puis prédiction de rupture (station vide
ou pleine à H+30) quand trois semaines d'historique propre seront accumulées.
Déploiement AWS Fargate comme deuxième environnement.

## Licence

Données Vélib' Métropole et Ville de Paris sous licence ODbL. Données Open-Meteo
selon leurs conditions d'utilisation.
