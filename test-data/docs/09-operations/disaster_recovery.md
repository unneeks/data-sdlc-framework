# Disaster Recovery Plan — Project ATLAS

**Document ID:** ATLAS-OPS-DR-001  
**Version:** 1.3  
**Last Updated:** 2025-05-20  
**Owner:** Platform SRE Team  
**Classification:** Confidential  
**Next Review:** 2025-11-20  
**Approved By:** CTO, Head of Data Engineering, CISO  

---

## 1. Purpose and Scope

This document defines the disaster recovery (DR) plan for the ATLAS data platform. It establishes Recovery Point Objectives (RPO), Recovery Time Objectives (RTO), failover procedures, backup strategies, and DR drill schedules to ensure operational resilience as required by:

- **FCA PS21/3** — Building operational resilience
- **PRA SS1/21** — Operational resilience: Impact tolerances for important business services
- **Bank of England Supervisory Statement** — Outsourcing and third-party risk management

### 1.1 Scope

This plan covers:

- ATLAS Lakehouse (S3/Iceberg data layer)
- Streaming infrastructure (Amazon MSK)
- Compute layer (EKS clusters, Spark, Trino)
- Metadata services (AWS Glue Catalog, OpenMetadata)
- Serving layer (Trino, Superset)
- Supporting infrastructure (IAM, KMS, networking)

### 1.2 Out of Scope

- Source systems (Oracle DWH — covered by separate DR plan DR-ORACLE-001)
- Downstream consuming applications (covered by their respective DR plans)
- Network infrastructure (covered by Infrastructure DR plan DR-INFRA-001)

---

## 2. RPO and RTO Targets

### 2.1 Tier Definitions

| Tier | Description | RPO | RTO | Examples |
|------|-------------|-----|-----|----------|
| Tier 1 — Critical | Regulatory reporting feeds, real-time fraud detection, AML monitoring | 0 (zero data loss) | 1 hour | Transactions pipeline, fraud scoring, regulatory feeds |
| Tier 2 — Important | Customer-facing analytics, operational dashboards, risk calculations | 4 hours | 4 hours | Customer 360, risk aggregations, management reporting |
| Tier 3 — Standard | Internal analytics, ad-hoc queries, sandbox environments | 24 hours | 24 hours | Analyst sandboxes, experimental pipelines, dev environments |

### 2.2 Impact Tolerances (per FCA PS21/3)

| Important Business Service | Maximum Tolerable Disruption |
|---------------------------|------------------------------|
| Transaction Monitoring (AML) | 4 hours |
| Fraud Detection Scoring | 2 hours |
| Regulatory Reporting (FCA/PRA/BOE) | Report deadline - 4 hours |
| Customer Account Data Availability | 8 hours |
| Management Information | 24 hours |

---

## 3. Backup Strategy

### 3.1 Data Layer Backups

| Component | Backup Method | Frequency | Retention | Location |
|-----------|--------------|-----------|-----------|----------|
| S3 Lakehouse Data | S3 Cross-Region Replication | Continuous | 90 days versioning | eu-west-1 (Ireland) |
| S3 Lakehouse Data | S3 Glacier Deep Archive | Daily snapshot | 7 years | eu-west-2 (same region) |
| Iceberg Table Metadata | Iceberg snapshots + S3 versioning | Per commit (every write) | 30 days (snapshots), 90 days (metadata files) | eu-west-2 + eu-west-1 |
| AWS Glue Catalog | AWS Backup (daily) + Terraform state | Daily at 01:00 UTC | 30 days | eu-west-1 |
| MSK (Kafka) Topics | MSK multi-AZ replication (RF=3) + Tiered Storage | Continuous | 7 days hot, 30 days tiered | eu-west-2 (3 AZs) |
| OpenMetadata | RDS automated backups + cross-region read replica | Continuous + daily snapshot | 14 days | eu-west-2 + eu-west-1 |
| Trino Configuration | Git (Infrastructure-as-Code) + EKS ConfigMaps | Per change | Indefinite | GitHub + S3 |
| KMS Keys | AWS KMS multi-region keys | Continuous | N/A (managed service) | eu-west-2 + eu-west-1 |

### 3.2 Infrastructure State Backups

| Component | Method | Frequency | Retention |
|-----------|--------|-----------|-----------|
| Terraform State | S3 + DynamoDB locking | Per apply | 90 days versioning |
| EKS Cluster Config | Velero backup | Daily at 02:00 UTC | 30 days |
| Helm Release State | Git + Helm history | Per deploy | Indefinite |
| IAM Policies | Terraform state + AWS Config | Continuous | 90 days |
| Network Configuration | Terraform state + AWS Config | Per change | 90 days |

### 3.3 Backup Validation

| Validation Type | Frequency | Method |
|----------------|-----------|--------|
| Backup completeness check | Daily | Automated: verify backup exists and size > 0 |
| Restore test (sample tables) | Weekly | Restore 3 random Tier 1 tables, validate row counts |
| Full restore test (DR region) | Monthly | Complete platform restore in eu-west-1 |
| Cross-region consistency check | Daily | Compare Iceberg snapshot IDs across regions |

---

## 4. Disaster Scenarios and Response

### 4.1 Scenario 1: Single AZ Failure

**Impact:** Partial compute loss, no data loss  
**Probability:** Medium  
**Detection:** CloudWatch AZ health checks, EKS node count alerts

**Response Procedure:**

1. [Automatic] EKS reschedules pods to remaining AZs (< 5 minutes)
2. [Automatic] MSK continues operating on remaining brokers (RF=3)
3. [Manual if needed] Verify Trino worker count >= minimum threshold
4. [Manual if needed] Scale up replacement nodes in healthy AZs
5. [Verify] Run canary pipelines to confirm end-to-end functionality

**Expected Recovery:** < 15 minutes (automatic)

### 4.2 Scenario 2: Complete Region Failure (eu-west-2)

**Impact:** Full platform outage  
**Probability:** Very Low  
**Detection:** Route 53 health checks, cross-region monitoring from eu-west-1

**Response Procedure:**

1. **Declare DR Event** — Incident Commander confirms region failure (threshold: 15 min sustained outage)
2. **Activate DR Region** (eu-west-1):
   - Deploy EKS cluster from Terraform (pre-provisioned warm standby)
   - Activate S3 Cross-Region Replication target as primary
   - Deploy Trino/Spark/Superset from Helm charts
   - Point MSK Connect to DR Kafka cluster
3. **Data Validation:**
   - Verify Iceberg metadata consistency (last committed snapshot)
   - Identify data gap between last replication and failure
   - Quantify RPO breach if any
4. **Redirect Traffic:**
   - Update Route 53 DNS records to DR endpoints
   - Update downstream consumer configurations
   - Notify all data consumers of DR activation
5. **Operate in DR:**
   - Streaming pipelines resume from last Kafka offset
   - Batch pipelines restart from last successful checkpoint
   - Regulatory feeds switch to DR endpoints
6. **Communicate:**
   - Notify FCA/PRA if impact tolerance breached
   - Update status page and stakeholders every 30 minutes

**Expected Recovery:** 2-4 hours (within Tier 1 RTO for most services)

### 4.3 Scenario 3: Data Corruption (Logical Error)

**Impact:** Incorrect data in lakehouse, potential downstream impact  
**Probability:** Medium  
**Detection:** Data quality checks, reconciliation failures, user reports

**Response Procedure:**

1. **Isolate:** Identify affected tables and time range
2. **Stop Writes:** Pause pipelines writing to affected tables
3. **Rollback:** Use Iceberg time-travel to revert to last known-good snapshot:
   ```sql
   -- Identify good snapshot
   SELECT * FROM "atlas_lakehouse"."curated"."transactions$snapshots" ORDER BY committed_at DESC;
   
   -- Rollback
   CALL iceberg.system.rollback_to_snapshot('curated', 'transactions', <snapshot_id>);
   ```
4. **Root Cause:** Identify source of corruption (bad data, code bug, schema drift)
5. **Fix Forward:** Apply corrective transformation and resume pipelines
6. **Validate:** Run full quality checks and reconciliation
7. **Communicate:** Notify affected data consumers of data correction window

**Expected Recovery:** 1-4 hours depending on scope

### 4.4 Scenario 4: MSK (Kafka) Cluster Failure

**Impact:** Streaming ingestion halted  
**Probability:** Low  
**Detection:** MSK broker health, consumer lag spike, ingestion latency alert

**Response Procedure:**

1. [Automatic] MSK multi-AZ handles single broker failures
2. [If cluster-wide] Activate standby MSK cluster (pre-provisioned)
3. Redirect Debezium connectors to standby cluster
4. Redirect Spark Structured Streaming consumers
5. Verify consumer groups resume from correct offsets
6. Monitor for data gaps and reconcile

**Expected Recovery:** 30 minutes (single broker), 2 hours (cluster-wide)

### 4.5 Scenario 5: Ransomware / Security Breach

**Impact:** Data encryption/exfiltration, platform compromise  
**Probability:** Low  
**Detection:** GuardDuty, anomalous access patterns, encryption activity

**Response Procedure:**

1. **Isolate immediately:** Revoke all access, disable network connectivity
2. **Preserve evidence:** Snapshot all affected resources, preserve CloudTrail logs
3. **Engage Security:** CISO, Incident Response Team, and if needed external forensics
4. **Assess scope:** Determine affected data, timeframe, and blast radius
5. **Restore from clean backup:** Use immutable backups (S3 Object Lock / Glacier Vault Lock)
6. **Regulatory notification:** ICO within 72 hours if personal data affected; FCA/PRA if operational resilience impacted
7. **Rebuild:** Provision fresh infrastructure, restore data, rotate all credentials

**Expected Recovery:** 24-72 hours (dependent on scope)

---

## 5. DR Infrastructure

### 5.1 Warm Standby Components (eu-west-1)

| Component | Standby State | Activation Time |
|-----------|--------------|-----------------|
| EKS Cluster | Pre-provisioned (0 worker nodes) | 15 minutes (scale up) |
| S3 Data | Continuously replicated | 0 (already available) |
| MSK Cluster | Provisioned (minimal throughput) | 30 minutes (scale up) |
| Glue Catalog | Daily backup restore script | 30 minutes |
| RDS (OpenMetadata) | Cross-region read replica | 10 minutes (promote) |
| Trino | Helm chart ready, no running pods | 15 minutes |
| KMS Keys | Multi-region keys active | 0 (already available) |
| IAM Roles | Pre-created via Terraform | 0 (already available) |

### 5.2 Cost of DR Standby

| Component | Monthly Cost (Standby) | Monthly Cost (Active) |
|-----------|----------------------|----------------------|
| S3 CRR | ~GBP 2,400 | Same |
| EKS Control Plane | ~GBP 55 | ~GBP 55 |
| MSK (minimal) | ~GBP 800 | ~GBP 4,500 |
| RDS Read Replica | ~GBP 450 | ~GBP 450 |
| Total DR Standby | ~GBP 3,705/month | — |

---

## 6. DR Drill Schedule

### 6.1 Drill Types

| Drill Type | Description | Frequency | Duration | Participants |
|-----------|-------------|-----------|----------|-------------|
| Tabletop Exercise | Walk through DR scenarios on paper | Quarterly | 2 hours | All engineering + management |
| Component Failover | Fail individual component, verify auto-recovery | Monthly | 1 hour | Platform SRE |
| Data Restore Test | Restore Tier 1 tables from backup, validate integrity | Monthly | 4 hours | Data Engineering |
| Partial DR Activation | Activate DR region, run pipelines in read-only mode | Quarterly | 8 hours | All engineering |
| Full DR Failover | Complete failover to DR region, operate for 24 hours | Annually | 24 hours | All teams + stakeholders |

### 6.2 Annual DR Drill Calendar

| Month | Drill | Scope |
|-------|-------|-------|
| January | Tabletop: Region failure | All teams |
| February | Component: MSK broker failure | SRE |
| March | Data Restore: Transactions table | Data Engineering |
| April | Tabletop: Ransomware scenario | All teams + CISO |
| May | Component: EKS node failure | SRE |
| June | Partial DR: Activate eu-west-1, validate data consistency | All engineering |
| July | Tabletop: Data corruption scenario | Data Engineering + Governance |
| August | Component: Trino coordinator failover | SRE |
| September | Data Restore: Full curated schema | Data Engineering |
| October | Full DR Failover (annual) | All teams + business stakeholders |
| November | Component: Glue Catalog restore | Data Engineering |
| December | Tabletop: Year-end lessons learned | All teams |

### 6.3 Drill Success Criteria

| Criterion | Target |
|-----------|--------|
| Recovery within RTO | 100% of drills |
| Data loss within RPO | 100% of drills |
| All runbook steps executable | 100% |
| No manual steps requiring unavailable knowledge | 100% |
| Post-drill issues resolved within 14 days | 100% |

---

## 7. Communication Plan

### 7.1 Internal Communication

| Audience | Channel | Frequency During DR |
|----------|---------|-------------------|
| Engineering Team | Slack #atlas-incidents | Continuous |
| Management | Email + Bridge call | Every 30 minutes |
| Business Stakeholders | Email + Status Page | Every 1 hour |
| Compliance/Risk | Email + Phone | Immediately on activation + hourly |

### 7.2 External Communication

| Audience | Channel | Trigger |
|----------|---------|---------|
| FCA/PRA | Regulatory notification portal | Impact tolerance breach |
| ICO | Breach notification portal | Personal data affected |
| Downstream Consumers | API status endpoint + Email | Any DR activation |
| Third-Party Vendors | Contractual notification | As per contract terms |

---

## 8. Post-DR Review

After every DR event (real or drill):

1. **Incident Timeline:** Document minute-by-minute actions taken
2. **Impact Assessment:** Quantify data loss, downtime, affected consumers
3. **Root Cause Analysis:** 5-Whys analysis of failure cause
4. **Gap Identification:** What didn't work as planned?
5. **Action Items:** Assigned, prioritised improvements with deadlines
6. **Plan Update:** Update this DR plan within 14 days of event
7. **Regulatory Reporting:** If applicable, complete FCA/PRA incident report

---

## 9. Dependencies and Contacts

### 9.1 Key Contacts

| Role | Name | Contact | Backup |
|------|------|---------|--------|
| Incident Commander | Platform Engineering Manager | PagerDuty escalation | Head of Data Engineering |
| DR Coordinator | Lead SRE | PagerDuty escalation | Senior SRE |
| Data Engineering Lead | Senior Data Engineer | PagerDuty escalation | Data Engineer (on-call) |
| Security Lead | CISO | Phone (24/7) | Deputy CISO |
| Compliance Contact | Head of Compliance | Phone (24/7) | Compliance Manager |
| AWS Support | Enterprise Support | AWS Support Console (Critical) | TAM |

### 9.2 External Dependencies

| Dependency | Impact if Unavailable | Mitigation |
|-----------|----------------------|------------|
| AWS eu-west-2 | Full platform outage | DR in eu-west-1 |
| AWS Glue | No metadata access | Local Hive Metastore failover |
| AWS KMS | Cannot decrypt data | Multi-region keys in DR region |
| PagerDuty | No alert routing | Fallback to SNS + direct phone tree |
| GitHub | No IaC deployments | Local Terraform state + cached charts |
