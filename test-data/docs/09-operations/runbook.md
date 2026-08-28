# Operational Runbook — Project ATLAS

## On-Call Structure

| Tier | Team | Hours | Escalation |
|------|------|-------|------------|
| L1 | Data Platform SRE | 24/7 (PagerDuty rotation) | 15 min response |
| L2 | Data Engineering | Business hours + on-call | Escalated from L1 after 30 min |
| L3 | Architecture / Vendor | Business hours | Escalated from L2 for platform-level issues |

## Common Incidents

### INC-001: Batch Pipeline SLA Breach

**Symptom**: `daily_dbt_dag` has not completed by 06:00 UTC.

**Diagnosis**:
```bash
# Check Airflow DAG status
aws mwaa cli --name atlas-prod --command "dags state daily_dbt_dag $(date +%Y-%m-%d)"

# Check for failed tasks
aws mwaa cli --name atlas-prod --command "tasks failed daily_dbt_dag $(date +%Y-%m-%d)"

# Check EMR Serverless job status
aws emr-serverless list-job-runs --application-id $APP_ID --states FAILED
```

**Resolution**:
1. If single task failed → restart from failed task: `airflow tasks run daily_dbt_dag <task_id> <execution_date>`
2. If EMR capacity issue → check service quotas, retry with `--conf spark.executor.instances=<lower>`
3. If source system delay → wait + notify downstream consumers of delayed SLA

---

### INC-002: Kafka Consumer Lag Spike

**Symptom**: CloudWatch alarm `atlas-kafka-lag-critical` firing.

**Diagnosis**:
```bash
# Check consumer group lag
aws kafka describe-consumer-group --cluster-arn $CLUSTER_ARN \
  --consumer-group-id atlas-cdc-consumer

# Check broker health
aws kafka describe-cluster --cluster-arn $CLUSTER_ARN
```

**Resolution**:
1. If consumer crashed → restart Spark Streaming job from last checkpoint
2. If broker unhealthy → failover (MSK handles automatically, verify replication)
3. If sustained high volume → increase consumer parallelism (add Spark executors)

---

### INC-003: Data Quality Alert

**Symptom**: Slack alert in #dq-alerts from Great Expectations or Soda.

**Diagnosis**:
```bash
# View failed expectations
aws s3 cp s3://atlas-prod-quality/reports/latest/ ./reports/ --recursive
# Open reports/index.html for detailed failure breakdown

# Check if source data is the issue
SELECT COUNT(*), MIN(updated_at), MAX(updated_at)
FROM raw.source_table
WHERE ingestion_date = CURRENT_DATE;
```

**Resolution**:
1. If source schema changed → update schema registry, notify Data Architect
2. If volume anomaly → verify with source system owner (planned maintenance?)
3. If referential integrity failure → quarantine affected records, investigate upstream

---

### INC-004: Trino Query Performance Degradation

**Symptom**: P95 query latency exceeds 10s threshold.

**Diagnosis**:
```bash
# Check active queries
trino-cli --execute "SELECT * FROM system.runtime.queries WHERE state = 'RUNNING'"

# Check worker count
kubectl get pods -n trino -l component=worker

# Check for resource pressure
kubectl top nodes -l workload=trino
```

**Resolution**:
1. If single expensive query → identify and kill: `CALL system.runtime.kill_query('<query_id>')`
2. If under-scaled → verify HPA is responding, manually scale if needed
3. If data skew → check Iceberg table statistics, trigger OPTIMIZE on skewed tables

---

### INC-005: Iceberg Table Corruption / Metadata Issue

**Symptom**: Queries return errors referencing snapshot or manifest files.

**Diagnosis**:
```bash
# List recent snapshots
spark-sql --conf spark.sql.catalog.atlas=org.apache.iceberg.spark.SparkCatalog \
  -e "SELECT * FROM atlas.db.table.snapshots ORDER BY committed_at DESC LIMIT 10"
```

**Resolution**:
1. Time-travel to last known-good snapshot: `ALTER TABLE t SET TBLPROPERTIES('current-snapshot-id' = '<id>')`
2. If orphaned files → run `CALL atlas.system.remove_orphan_files(table => 't')`
3. If metadata corruption → restore metadata from S3 versioning

## Scheduled Maintenance

| Task | Frequency | Procedure |
|------|-----------|-----------|
| Iceberg table compaction | Daily 22:00 UTC | Airflow DAG `maintenance_compaction` |
| Expire old snapshots | Weekly (Sunday) | Airflow DAG `maintenance_snapshot_expiry` |
| Kafka topic cleanup | Weekly | Retention policy (7 days for CDC, 30 days for audit) |
| Certificate rotation check | Monthly | Automated scan, alert if < 30 days remaining |
| Disaster recovery drill | Quarterly | Full failover to eu-west-1, documented results |

## Monitoring Dashboards

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| Pipeline Health | grafana.internal/d/atlas-pipelines | DAG success rates, durations, SLA tracking |
| Data Quality | grafana.internal/d/atlas-quality | GE/Soda pass rates, trend charts |
| Infrastructure | grafana.internal/d/atlas-infra | CPU, memory, disk, network across all components |
| Cost | grafana.internal/d/atlas-cost | Daily spend, forecast, anomaly detection |
| Kafka | grafana.internal/d/atlas-kafka | Throughput, lag, broker health |
