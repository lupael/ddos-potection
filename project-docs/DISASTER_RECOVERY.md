# Disaster Recovery Runbook — DDoS Protection Platform

> **Version:** 1.0 · **Last updated:** 2026-03-26
>
> This runbook provides step-by-step procedures for recovering the DDoS Protection Platform
> from common failure scenarios.

---

## Recovery Objectives

| Metric | Target |
|---|---|
| **RTO** (Recovery Time Objective) | 4 hours |
| **RPO** (Recovery Point Objective) | 15 minutes |
| **MTTR** (Mean Time To Recover) | < 2 hours |

---

## Failure Scenarios

### 1. PostgreSQL Database Failure

**Symptoms:**
- `/health/ready` returns `503` with `"postgres"` in errors
- Application logs show `OperationalError` / `connection refused`

**Recovery Steps:**

```bash
# Step 1 — Check PostgreSQL status
systemctl status postgresql   # bare metal
kubectl get pods -l app=postgres   # Kubernetes

# Step 2 — Attempt restart
systemctl restart postgresql   # bare metal
kubectl rollout restart deployment/postgres   # Kubernetes

# Step 3 — If data corruption, restore from PITR backup
# 3a. Stop PostgreSQL
systemctl stop postgresql

# 3b. Download latest base backup from S3
export BACKUP_BUCKET=your-bucket
export BACKUP_PREFIX=ddos-platform/backups
aws s3 ls s3://${BACKUP_BUCKET}/${BACKUP_PREFIX}/base/ --recursive | sort | tail -5
aws s3 cp s3://${BACKUP_BUCKET}/${BACKUP_PREFIX}/base/basebackup_TIMESTAMP.tar.gz /tmp/

# 3c. Restore base backup
rm -rf /var/lib/postgresql/data
mkdir -p /var/lib/postgresql/data
cd /var/lib/postgresql/data
tar -xzf /tmp/basebackup_TIMESTAMP.tar.gz

# 3d. Create recovery.conf (PostgreSQL < 12) or recovery signal (PostgreSQL >= 12)
touch /var/lib/postgresql/data/recovery.signal
cat >> /var/lib/postgresql/data/postgresql.conf << 'EOF'
restore_command = 'aws s3 cp s3://${BACKUP_BUCKET}/${BACKUP_PREFIX}/wal/%f %p'
recovery_target_time = '2026-03-26 12:00:00 UTC'
EOF

# 3e. Start PostgreSQL — it will replay WAL segments
systemctl start postgresql

# Step 4 — Verify recovery
psql -U ddos_user -d ddos_platform -c "SELECT count(*) FROM isps;"
curl http://localhost:8000/health/ready
```

---

### 2. Redis Failure

**Symptoms:**
- `/health/ready` returns `503` with `"redis"` in errors
- Alert pipeline stops; detector switches to fallback polling

**Recovery Steps (Sentinel Mode):**

```bash
# Step 1 — Check Sentinel status
redis-cli -h redis-sentinel -p 26379 SENTINEL masters

# Step 2 — Identify and connect to new primary
MASTER=$(redis-cli -h redis-sentinel -p 26379 SENTINEL get-master-addr-by-name mymaster)
echo "New primary: $MASTER"

# Step 3 — Force failover if needed
redis-cli -h redis-sentinel -p 26379 SENTINEL failover mymaster

# Step 4 — Verify application reconnected
curl http://localhost:8000/health/ready

# Step 5 — Docker Compose restart
docker-compose restart redis-master redis-replica redis-sentinel
```

**Recovery Steps (Single Redis, no Sentinel):**

```bash
# Restart Redis
docker-compose restart redis
# Or bare metal:
systemctl restart redis

# Verify
redis-cli ping   # should return PONG
curl http://localhost:8000/health/ready
```

> **Note:** Redis data is ephemeral (caches, flow counters). Loss of Redis data is tolerable —
> the platform reconstructs state from PostgreSQL and incoming flows within one polling cycle.

---

### 3. API Service Failure

**Symptoms:**
- HTTP 502/503 from upstream proxy/load balancer
- No pods in `Running` state

**Kubernetes Recovery:**

```bash
# Step 1 — Check pod state
kubectl get pods -l app=ddos-backend -o wide
kubectl describe pod <pod-name>

# Step 2 — Check logs
kubectl logs <pod-name> --previous --tail=100

# Step 3 — Restart deployment
kubectl rollout restart deployment/ddos-backend

# Step 4 — Monitor rollout
kubectl rollout status deployment/ddos-backend --timeout=300s

# Step 5 — Scale up if needed
kubectl scale deployment/ddos-backend --replicas=3

# Step 6 — Verify
curl http://api-endpoint/health/ready
```

**Docker Compose Recovery:**

```bash
docker-compose restart backend
docker-compose logs --tail=50 backend
```

---

### 4. Full Site Failure (Total Cluster Loss)

**Symptoms:**
- All pods/containers down
- Storage volumes inaccessible

**Recovery Steps:**

```bash
# Step 1 — Provision new cluster / VMs
# (Follow deployment guide: project-docs/DEPLOYMENT.md)

# Step 2 — Restore secrets
# From HashiCorp Vault or Kubernetes External Secrets:
kubectl apply -f kubernetes/vault-secret-store.yaml
kubectl apply -f kubernetes/external-secrets.yaml

# Step 3 — Apply Kubernetes manifests
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/hpa.yaml
kubectl apply -f kubernetes/network-policies.yaml
kubectl apply -f kubernetes/pdb.yaml

# Step 4 — Restore PostgreSQL from PITR backup (see Section 1, Step 3)

# Step 5 — Run Alembic migrations
cd backend && alembic upgrade head

# Step 6 — Verify all services
curl http://api-endpoint/health/ready
curl http://api-endpoint/health/live
```

---

## Health Check Verification

After any recovery action, verify platform health in this order:

```bash
# 1. Liveness probe
curl -f http://localhost:8000/health/live
# Expected: {"status": "alive"}

# 2. Readiness probe (DB + Redis)
curl -f http://localhost:8000/health/ready
# Expected: {"status": "ready"}

# 3. Prometheus metrics
curl -s http://localhost:8000/metrics | grep 'ddos_alerts_total'

# 4. API authentication
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=YOURPASSWORD" | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/alerts

# 5. Verify Grafana
curl -u admin:admin http://localhost:3001/api/health
```

---

## WAL Archive Configuration

To enable continuous WAL archiving, add to `postgresql.conf`:

```ini
archive_mode = on
archive_command = 'WAL_PATH=%p WAL_NAME=%f BACKUP_BUCKET=your-bucket bash /opt/scripts/pg_backup.sh --wal-archive'
archive_timeout = 300   # archive at least every 5 minutes
```

Trigger a base backup via cron (daily recommended):

```cron
0 2 * * * BACKUP_BUCKET=your-bucket PGPASSWORD=secret bash /opt/scripts/pg_backup.sh --full >> /var/log/pg_backup.log 2>&1
```

---

## Contact Escalation Matrix

| Severity | First Contact | Escalate After | Second Contact |
|---|---|---|---|
| P1 — Total outage | On-call engineer | 15 min | Engineering lead |
| P2 — Partial degradation | On-call engineer | 30 min | Engineering lead |
| P3 — Performance issue | Ops team | 2 hours | Engineering lead |
| P4 — Non-urgent | Ops team | Next business day | — |

---

## Useful Commands Quick Reference

```bash
# Alembic migrations
cd backend && alembic upgrade head
cd backend && alembic current

# Rebuild Docker images
docker-compose build --no-cache backend

# Drain a Kubernetes node gracefully
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Force pod eviction
kubectl delete pod <pod-name> --grace-period=0 --force

# Check PodDisruptionBudgets
kubectl get pdb

# Scale down for maintenance
kubectl scale deployment/ddos-backend --replicas=0

# Check ExternalSecrets sync status
kubectl get externalsecret
```

---

*Reviewed quarterly. Next review: Q2 2026.*
