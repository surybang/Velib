# Service `dbt`

Transforme les données brutes de la couche bronze en une table de faits,
`gold.fct_velib_meteo`, qui joint chaque snapshot de station à la mesure météo
la plus proche et ajoute les features calendaires.

## Lignage

```
bronze.velib_stations ──> stg_velib ──┐
                                      ├──> int_velib_meteo ──> fct_velib_meteo
bronze.meteo_paris    ──> stg_meteo ──┘
```

| Couche | Schéma | Matérialisation | Ce qu'elle fait |
|---|---|---|---|
| Sources | `bronze` | tables | Données brutes écrites par `ingestion/` |
| Staging | `silver` | vues | Renommage, typage, `OUI`/`NON` en booléens |
| Intermediate | `silver` | vue | Jointure Vélib' × météo, filtre des stations inactives |
| Marts | `gold` | table | Features calendaires, `occupancy_rate`, cibles `is_empty` et `is_full` |

Les vues se recalculent à chaque lecture. La table gold est reconstruite à chaque
`dbt run`, ce qui prend environ une seconde sur 150 000 lignes.

## Utilisation

```bash
uv sync
uv run dbt deps              # une fois, ou après modification de packages.yml
uv run dbt debug             # vérifie la connexion
uv run dbt source freshness  # la collecte a-t-elle décroché ?
uv run dbt run
uv run dbt test              # 27 tests
```

Les identifiants viennent de l'environnement via `profiles.yml` :
`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`.

`dbt_packages/` est ignoré par git. `dbt deps` le régénère localement et le
Dockerfile le régénère dans l'image.

## Décisions de modélisation

**Jointure par LATERAL.** Les deux flux ont une granularité de 15 minutes mais
pas la même horloge. Un `LATERAL JOIN` avec fenêtre de ±15 minutes retient pour
chaque snapshot la mesure météo la plus proche, sans supposer que les deux
tombent à la même minute.

**Tout reste en UTC.** Les colonnes `duedate`, `meteo_measured_at` et
`ingested_at` sont des `timestamptz`. Les features calendaires (`hour_of_day`,
`day_of_week`, `is_weekend`) sont calculées avec `AT TIME ZONE 'Europe/Paris'`
mais les timestamps eux-mêmes ne sont jamais convertis en base. Une version
précédente castait en `::TIMESTAMP` après conversion, ce qui produisait des
timestamps naïfs réinterprétés en UTC lors de comparaisons avec `NOW()`. Deux
heures de décalage silencieux en été.

**`duedate` pour la jointure, `ingested_at` pour la freshness.** `duedate` est
l'horodatage métier de l'API. Il subit un cache de 15 minutes mais reste l'axe
correct pour joindre avec la météo. `ingested_at` est l'horloge du pipeline et
sert uniquement à `dbt source freshness`, qui alerte si aucune ligne n'a été
insérée depuis 45 minutes.

**`occupancy_rate` plafonné à 100.** La station 15056 (Place Balard) déclare
`capacity = 22` mais accueille jusqu'à 42 vélos, soit un taux de 190 %. Le
`LEAST(..., 100)` empêche cette anomalie de métadonnée de contaminer
l'entraînement d'un modèle.

**Dénominateur sur `capacity`, pas sur `bikes + docks`.** Le second varie quand
des bornettes tombent en panne, ce qui injecterait du bruit d'équipement dans une
variable cible. La capacité théorique est stable par station.

**Granularité verrouillée.** `unique_combination_of_columns` sur
`(stationcode, duedate)` à chaque couche. Un doublon d'ingestion serait détecté
au premier `dbt test`.

## Diagnostiquer les trous de collecte

```bash
uv run dbt show --select analyses_gap --limit 20
```

`analyses/analyses_gap.sql` calcule l'écart entre snapshots successifs sur
`ingested_at` et liste les pauses de plus de 20 minutes. Les analyses dbt sont
compilées mais jamais matérialisées, ce qui permet de versionner une requête de
diagnostic avec le templating `ref()` et `source()` sans créer d'objet en base.

## Lint SQL

sqlfluff tourne au commit via prek, avec la config dans `.sqlfluff` à la racine.
Virgules en début de ligne, mots-clés en majuscules, 100 caractères max.

Les règles `ST06`, `RF04`, `LT02`, `LT04`, `RF02`, `RF03` et `AL01` sont
exclues. La plupart donnent des faux positifs sur le `LATERAL JOIN` avec le
templater dbt.
