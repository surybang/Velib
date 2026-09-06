# Notes sur les APIs sources

Deux fichiers qui documentent les particularités des APIs observées pendant le
développement. Utile pour comprendre pourquoi le pipeline fait certains choix.

| Fichier | API |
|---|---|
| `Open_Data_Paris.md` | Vélib' disponibilité temps réel, via Opendatasoft |
| `meteo.md` | Open-Meteo, mesures pour Paris |

## Le point qui a coûté le plus de temps

L'endpoint paginé d'Opendatasoft (`/records?limit=100&offset=N`) est servi
depuis un cache rafraîchi toutes les 15 minutes environ. L'endpoint ciblé
(`?where=stationcode=12007`) ne l'est pas. Sur la même station au même instant,
un `curl` ciblé renvoyait `duedate = 11:54` quand la base, alimentée par le
paginé, contenait `10:54`.

La collecte utilise le paginé parce qu'il faut les 995 stations en 10 requêtes,
pas en 995. Le prix est un `duedate` qui peut avoir jusqu'à 15 minutes de retard.
C'est acceptable pour l'analyse, et la colonne `ingested_at` posée par la base
donne l'heure réelle de collecte quand on en a besoin.
