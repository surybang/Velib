# Service `ingestion`

Interroge les APIs Vélib' et Open-Meteo, aplatit la réponse, et écrit dans la
couche bronze de PostgreSQL. Aucune transformation métier, ça vit dans `dbt/`.

## Deux tâches indépendantes

| Commande | Ce qu'elle fait | Table |
|---|---|---|
| `ingest-velib` | Récupère les 995 stations en 10 requêtes paginées | `bronze.velib_stations` |
| `ingest-meteo` | Récupère la mesure météo courante pour Paris | `bronze.meteo_paris` |

Chaque commande est un processus court qui fait une chose puis sort. La
périodicité est gérée par Airflow, pas par le code.

## Utilisation

```bash
uv sync
uv run ingest-velib
uv run ingest-meteo
uv run pytest        # 16 tests, sans réseau ni base
```

## Configuration

Toutes les variables sont lues depuis l'environnement, sans valeur par défaut
pour les secrets. Une variable manquante fait planter le démarrage plutôt que de
pointer silencieusement ailleurs.

| Variable | Rôle |
|---|---|
| `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` | Connexion PostgreSQL |
| `VELIB_API_BASE_URL` | Endpoint records Opendatasoft |
| `VELIB_API_PAGE_SIZE` | Taille de page, 100 par défaut |
| `METEO_API_BASE_URL` | Endpoint Open-Meteo avec ses paramètres |
| `LOG_LEVEL` | Niveau loguru, `INFO` par défaut |
| `JSON_LOGS` | `true` en conteneur pour des logs structurés |

En prod, le Secret Kubernetes `velib-postgres-credentials` et le ConfigMap
`velib-config` fournissent ces valeurs (voir `deploy/sspcloud/`).

## Structure

```
src/velib_ingestion/
├── config.py           pydantic-settings, validation au démarrage
├── db.py               connexion PostgreSQL, ouverte et fermée par run
├── logging_setup.py    loguru, JSON si JSON_LOGS=true
├── fetchers/
│   ├── velib_fetcher.py    pagination, aplatissement, insertion groupée
│   └── meteo_fetcher.py    parsing, fuseau horaire, insertion
└── entrypoints/
    ├── runner.py           logging + traduction exception → exit code
    ├── velib.py            ingest-velib
    └── meteo.py            ingest-meteo
```

## Décisions

**Connexion par run.** Une connexion maintenue entre deux exécutions est fermée
par le serveur après quelques minutes d'inactivité. psycopg2 ne le détecte qu'au
moment de l'utiliser, ce qui produit un `SSL SYSCALL error: EOF detected` en
pleine insertion. Chaque run ouvre donc la sienne.

**Insertion groupée.** `execute_values` envoie les 995 stations en une requête.
Un `execute` par ligne faisait 995 allers-retours.

**Exceptions propagées.** Les fetchers ne capturent pas leurs erreurs. Elles
remontent jusqu'à `runner.py` qui sort en code 1. Airflow voit l'échec. Un
fetcher qui log l'erreur et continue en code 0 aurait masqué trois semaines de
trou en juillet.

**Fuseau météo explicite.** Open-Meteo renvoie `"2026-07-02T21:45"` sans suffixe
de fuseau, en heure de Paris. Sans le tag `Europe/Paris` posé avant insertion,
psycopg2 l'interprète comme UTC et la mesure se retrouve décalée de deux heures
en été. Le test `test_attache_le_fuseau_paris` vérifie ce cas.

**Cache de l'API.** L'endpoint paginé Opendatasoft est rafraîchi toutes les
15 minutes environ. Le `duedate` d'une station peut donc avoir jusqu'à 15 minutes
de retard sur son état réel. Le champ `ingested_at`, posé par la base, reste
l'horloge fiable du pipeline.

## Tests

Les 16 tests interceptent les appels HTTP avec `respx` et ne touchent jamais la
base. Ils couvrent l'aplatissement des coordonnées, la pagination, la propagation
des erreurs réseau, et le cas du fuseau horaire météo.
