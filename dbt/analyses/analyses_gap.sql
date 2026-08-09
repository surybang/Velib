-- Détecte les pauses de collecte : écart entre deux snapshots distincts.
-- Basé sur ingested_at (l'horloge du pipeline), pas duedate (soumis au cache API).
WITH snapshots AS (
    SELECT DISTINCT date_trunc('minute', ingested_at) AS run_at
    FROM {{ source('bronze', 'velib_stations') }}
),
gaps AS (
    SELECT
        run_at,
        LAG(run_at) OVER (ORDER BY run_at) AS previous_run,
        run_at - LAG(run_at) OVER (ORDER BY run_at) AS gap
    FROM snapshots
)
SELECT
    previous_run AT TIME ZONE 'Europe/Paris' AS pause_debut_paris,
    run_at       AT TIME ZONE 'Europe/Paris' AS reprise_paris,
    gap AS duree_pause
FROM gaps
WHERE gap > INTERVAL '20 minutes'   -- au-delà d'un cycle de 15 min manqué
ORDER BY gap DESC