# Service `dbt` — Transformation Vélib'

Transforme les données brutes collectées par le service `ingestion` en une
table de faits exploitable pour l'analyse et le ML.

## Architecture médaillon

```
bronze.velib_stations  ──> stg_velib  ──┐
                                        ├──> int_velib_meteo ──> fct_velib_meteo
bronze.meteo_paris     ──> stg_meteo  ──┘
```

| Couche | Schéma | Type | Rôle |
|---|---|---|---|
| Staging | `silver` | vue | Renommage, typage, drapeaux OUI/NON → booléens |
| Intermediate | `silver` | vue | Jointure Vélib × météo via LATERAL JOIN ±15 min |
| Marts | `gold` | table matérialisée | Features calendaires, cibles ML, table servie |

La table de faits `gold.fct_velib_meteo` est l'unique point de sortie.
Elle est reconstruite à chaque `dbt run`.

## Prérequis

Variables d'environnement requises (lues via `profiles.yml`) :

```
PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
```

En local, les poser dans un `.env` à la racine du repo et les exporter.
En prod, elles sont injectées depuis le Secret Kubernetes `velib-postgres-credentials`.

## Installation et utilisation

```bash
cd dbt
uv sync

# À lancer une fois après le clone, ou après modification de packages.yml
# Télécharge dbt_utils dans dbt_packages/ (non versionné)
uv run dbt deps

# Vérifier la connexion et la config
uv run dbt debug

# Vérifier que les sources sont fraîches (collecte en cours)
uv run dbt source freshness

# Construire les modèles
uv run dbt run

# Lancer les tests
uv run dbt test

# Analyser les trous de collecte
uv run dbt show --select analyses_gap --limit 20
```

## Packages

`dbt_utils` (dbt-labs) fournit les macros de test :
`unique_combination_of_columns`, `accepted_range`, `expression_is_true`.

Le dossier `dbt_packages/` est ignoré par git. Il est recréé par `dbt deps`
et installé dans l'image Docker via `RUN dbt deps --project-dir /app`.

## Décisions de modélisation

### Jointure Vélib × météo

Les deux flux ont une granularité de 15 min mais ne sont pas alignés sur la
même horloge. Un `LATERAL JOIN` avec fenêtre ±15 min retient la mesure météo
la plus proche de chaque snapshot, sans dépendre d'une coïncidence
d'horodatage.

### Convention temporelle

Tous les timestamps sont stockés en UTC (`timestamptz`). La conversion en
heure de Paris n'a lieu qu'à l'affichage ou pour dériver les features
calendaires (`hour_of_day`, `day_of_week`, `month`, `is_weekend`).

### `duedate` vs `ingested_at`

`duedate` est l'horodatage API, soumis au cache Opendatasoft (~15 min de
retard possible). Il sert à la jointure métier et à l'analyse temporelle.

`ingested_at` est l'horloge du pipeline (posée par PostgreSQL à l'insertion).
Elle sert uniquement à la freshness dbt, qui surveille la santé de la
collecte, pas l'état des données.

### `occupancy_rate`

Calculé comme `bikes_available / capacity * 100`, plafonné à 100 via `LEAST`.
La station 15056 (Place Balard) a une `capacity` mal déclarée (22) mais
accueille régulièrement 40+ vélos, produisant des taux jusqu'à 190%.
Le plafonnement évite de propager cette anomalie vers les couches ML.

### Granularité garantie par test

`unique_combination_of_columns` sur `(stationcode, duedate)` vérifie à chaque
couche qu'une ligne représente bien un snapshot de station.

## Analyse des trous de collecte

`analyses/analyses_gap.sql` identifie les pauses de collecte en calculant
l'écart entre snapshots successifs, basé sur `ingested_at`.

```bash
uv run dbt show --select analyses_gap --limit 20
```

## Qualité du code SQL

sqlfluff est configuré dans `.sqlfluff` à la racine du repo.
Lancé automatiquement par prek au commit.

```bash
uv run sqlfluff lint models/
uv run sqlfluff fix models/
```
