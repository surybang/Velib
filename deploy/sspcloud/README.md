# Déploiement SSP Cloud (Onyxia)

Configuration Kubernetes pour faire tourner le pipeline Vélib' sur SSP Cloud.
Contient le RBAC pour le KubernetesPodOperator d'Airflow, les exemples de
Secret et ConfigMap, et la procédure de mise en route et de récupération
après coupure.

## Architecture

```
Airflow (catalogue Onyxia, CeleryExecutor)
  └── worker : KubernetesPodOperator
        ├── pod velib-ingestion → ingest-velib / ingest-meteo
        └── pod velib-dbt       → dbt run / dbt test / dbt source freshness

PostgreSQL : postgresql-cnpg-114514-rw (CloudNativePG, persistant)
Images     : ghcr.io/surybang/velib-ingestion et velib-dbt
```

## Prérequis

- Avoir un VSCode **admin** depuis le catalogue Onyxia
- Avoir des identifiants Kubernetes frais (Mon compte → Connexion cluster,
  valables `?` jours)
- Vérifier les droits :

```bash
kubectl auth can-i create pods
kubectl auth can-i create roles
kubectl auth can-i create rolebindings
# Les trois doivent répondre yes
```

---

## Mise en route initiale

### 1. Lancer Airflow depuis le catalogue

Lancer le service Airflow depuis le catalogue Onyxia avec git-sync configuré :

- **Repository** : `https://github.com/surybang/Velib.git`
- **Path** : `airflow/dags`
- **Branch** : `main`

### 2. Identifier le ServiceAccount du worker

```bash
kubectl get statefulset,deployment -n user-fabienhos \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.serviceAccountName}{"\n"}{end}' \
  | grep -i airflow
# Le worker affiche : airflow-XXXXXX-worker  airflow-XXXXXX
# Noter le numéro XXXXXX
```

### 3. Appliquer le RBAC

```bash
kubectl apply -f rbac/role.yaml

# Remplacer XXXXXX par le numéro du SA ci-dessus
kubectl create rolebinding airflow-pod-launcher \
  --role=airflow-pod-launcher \
  --serviceaccount=user-fabienhos:airflow-XXXXXX \
  -n user-fabienhos
```

Vérifier :

```bash
kubectl auth can-i create pods \
  --as=system:serviceaccount:user-fabienhos:airflow-XXXXXX \
  -n user-fabienhos
# Attendu : yes
```

### 4. Monter le token dans le worker

```bash
kubectl patch statefulset airflow-XXXXXX-worker -n user-fabienhos \
  --type merge \
  -p '{"spec":{"template":{"spec":{"automountServiceAccountToken":true}}}}'

# Attendre le redémarrage (1-2 min)
kubectl get pods -n user-fabienhos | grep airflow-XXXXXX-worker

# Vérifier le token
kubectl exec airflow-XXXXXX-worker-0 -n user-fabienhos \
  -- ls /var/run/secrets/kubernetes.io/serviceaccount/
# Attendu : ca.crt  namespace  token
```

### 5. Créer le Secret PostgreSQL

Récupérer les identifiants depuis le secret CNPG :

```bash
kubectl get secret -n user-fabienhos | grep cnpg
kubectl get secret postgresql-cnpg-114514-app -n user-fabienhos \
  -o jsonpath='{.data.username}' | base64 -d; echo
kubectl get secret postgresql-cnpg-114514-app -n user-fabienhos \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

Créer le Secret (ne jamais committer les vraies valeurs) :

```bash
kubectl create secret generic velib-postgres-credentials \
  --from-literal=PGHOST=postgresql-cnpg-114514-rw \
  --from-literal=PGPORT=5432 \
  --from-literal=PGDATABASE=defaultdb \
  --from-literal=PGUSER=<user> \
  --from-literal=PGPASSWORD=<password> \
  -n user-fabienhos
```

### 6. Créer le ConfigMap

```bash
kubectl apply -f secrets/velib-config.yaml
```

### 7. Vérification globale

```bash
kubectl get role,rolebinding,secret,configmap -n user-fabienhos \
  | grep -E "airflow-pod-launcher|velib-postgres|velib-config"
# 4 lignes attendues
```

### 8. Tester avec le DAG busybox

Dans l'UI Airflow, déclencher `test_pod_permissions` manuellement.
S'il passe vert, le PodOperator fonctionne.

---

## Après une coupure (checklist rapide)

À chaque relance du service Airflow, le numéro de SA change et le patch
du token est réconcilié. Reprendre depuis l'étape 2.

Le Role et le ConfigMap sont durables, pas besoin de les recréer.
Le Secret est durable sauf s'il a été supprimé.
Le RoleBinding et le patch du token sont à refaire.

Vérification rapide de l'état :

```bash
# 1. Nouveau numéro de SA ?
kubectl get statefulset -n user-fabienhos | grep worker

# 2. Token monté ?
kubectl exec airflow-XXXXXX-worker-0 -n user-fabienhos \
  -- ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>/dev/null \
  | grep token

# 3. Ressources présentes ?
kubectl get role,rolebinding,secret,configmap -n user-fabienhos \
  | grep -E "airflow-pod-launcher|velib-postgres|velib-config"
```

---

## Contexte et limites

**Pourquoi ce montage ?** La chart Bitnami déployée par le catalogue Onyxia
désactive le montage du ServiceAccount token par défaut
(`automountServiceAccountToken: false`), rendant le KubernetesPodOperator
inaccessible. On contourne en patchant le StatefulSet du worker après coup.

**Fragile par nature.** Le patch du token est appliqué par-dessus un
déploiement managé par le catalogue. Onyxia peut le réconcilier à `false`
lors d'une mise à jour ou relance du service. Le RoleBinding pointe un SA
nommé dont le numéro change à chaque relance.

**Solution durable.** Déployer Airflow via ArgoCD avec les valeurs Helm
qui fixent `automountServiceAccountToken: true` et un ServiceAccount dédié,
hors du catalogue managé.

---

## Diagnostiquer les trous de collecte

```bash
cd ~/work/Velib/dbt
uv run dbt show --select analyses_gap --limit 10
```

Affiche les pauses de collecte avec leur durée, basé sur `ingested_at`
(l'horloge du pipeline).
