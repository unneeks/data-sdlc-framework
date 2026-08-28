# Oracle DWH Decommission Plan — Project ATLAS

**Document ID:** ATLAS-TRN-DEC-001  
**Version:** 1.0  
**Last Updated:** 2025-06-15  
**Owner:** Programme Manager  
**Classification:** Confidential  
**Approved By:** CTO, CFO, Head of Data Engineering, Head of Compliance  

---

## 1. Executive Summary

This document defines the phased decommission plan for the Oracle Data Warehouse (DWH) following successful migration to the AWS lakehouse platform (Project ATLAS). The Oracle DWH has served as the bank's central analytical data store for 14 years. Decommission must be executed carefully to ensure zero data loss, maintain regulatory compliance with FCA/PRA record-keeping requirements, and realise the projected annual cost savings of GBP 2.8M in Oracle licensing.

### 1.1 Decommission Objectives

- Safely retire all Oracle DWH components with zero data loss
- Maintain regulatory compliance throughout the transition
- Realise Oracle licensing cost savings at the earliest responsible date
- Archive historical data per retention requirements (7+ years)
- Decommission associated infrastructure (servers, storage, network)
- Update all organisational documentation and processes

### 1.2 Decommission Scope

**In Scope:**

- Oracle Database Enterprise Edition (4-node RAC cluster)
- Oracle Exadata X8M storage
- Oracle GoldenGate replication infrastructure
- Oracle Data Integrator (ODI) ETL platform
- Oracle Business Intelligence Enterprise Edition (OBIEE) reports
- Associated middleware (WebLogic, Oracle HTTP Server)
- On-premises server hardware (Dell PowerEdge R740xd, 12 nodes)
- Oracle-specific network segments (VLAN 420, 421)
- Supporting storage (NetApp FAS8700 shelves allocated to DWH)

**Out of Scope:**

- Oracle core banking system (Flexcube) — remains operational
- Oracle CRM (Siebel) — separate decommission programme
- Non-DWH Oracle databases (OLTP, middleware)

---

## 2. Prerequisites

All prerequisites must be satisfied before decommission activities begin.

### 2.1 Migration Completeness

| Prerequisite | Verification Method | Status |
|-------------|-------------------|--------|
| All Tier 1 data domains migrated to ATLAS | Data inventory reconciliation | Pending |
| All Tier 2 data domains migrated to ATLAS | Data inventory reconciliation | Pending |
| All regulatory reports sourced from ATLAS | Report source validation | Pending |
| All downstream consumers migrated to ATLAS | Consumer registry check | Pending |
| Parallel run completed (minimum 3 months) | Reconciliation reports | Pending |
| Reconciliation variance < 0.001% for 30 consecutive days | Automated checks | Pending |
| All OBIEE reports rebuilt in Superset | Report migration tracker | Pending |
| Business sign-off on ATLAS data quality | Formal acceptance | Pending |

### 2.2 Regulatory Compliance

| Prerequisite | Verification Method | Status |
|-------------|-------------------|--------|
| FCA record-keeping obligations met by ATLAS | Compliance review | Pending |
| Historical data archived per retention policy | Archive completion report | Pending |
| Data lineage preserved for audit trail | OpenMetadata lineage check | Pending |
| DSAR (Subject Access Request) process updated | DPO confirmation | Pending |
| Regulatory reporting continuity confirmed | 3 successful report cycles | Pending |

### 2.3 Organisational Readiness

| Prerequisite | Verification Method | Status |
|-------------|-------------------|--------|
| BAU support model operational | Support model sign-off | Pending |
| All teams notified of decommission timeline | Communication log | Pending |
| Oracle DBA team redeployment/transition planned | HR confirmation | Pending |
| Vendor notification per contract terms | Procurement confirmation | Pending |
| Finance budget adjustment approved | CFO sign-off | Pending |

---

## 3. Phased Shutdown Plan

### Phase 1: Read-Only Mode (Weeks 1-4)

**Objective:** Stop all writes to Oracle DWH while maintaining read access for validation.

| Week | Action | Responsible | Verification |
|------|--------|-------------|-------------|
| W1 | Disable all ODI ETL jobs (write paths) | Oracle DBA Team | No new data in DWH tables |
| W1 | Disable GoldenGate replication to DWH | Oracle DBA Team | Replication status STOPPED |
| W1 | Revoke INSERT/UPDATE/DELETE privileges (all users) | Oracle DBA Team | Privilege audit report |
| W1 | Notify all users of read-only status | Communications | Acknowledgement receipts |
| W2 | Monitor for failed write attempts | Oracle DBA Team | Alert on ORA-01031 errors |
| W2 | Validate no active write dependencies | Application Team | Dependency scan results |
| W3-W4 | Continue read access for validation queries | All teams | Access logs confirm read-only |
| W4 | Final reconciliation: ATLAS vs Oracle (complete dataset) | Data Engineering | Variance < 0.001% |

**Rollback point:** If critical issues discovered, re-enable write paths within 4 hours.

### Phase 2: Access Restriction (Weeks 5-8)

**Objective:** Restrict access to essential users only. Confirm all consumers have migrated.

| Week | Action | Responsible | Verification |
|------|--------|-------------|-------------|
| W5 | Revoke access for all non-essential users | Oracle DBA Team | Reduced active sessions |
| W5 | Retain access for: Compliance, Audit, DBA team only | Oracle DBA Team | Access list < 20 users |
| W6 | Monitor connection attempts from revoked users | Oracle DBA Team | Zero blocked connection alerts |
| W6 | Contact any users still connecting — resolve dependency | Application Team | All dependencies resolved |
| W7 | OBIEE reports disabled (redirect to Superset) | BI Team | OBIEE scheduler stopped |
| W8 | Final opportunity for ad-hoc data extraction | All teams | Extract requests fulfilled |
| W8 | Compliance team confirms all required data accessible via ATLAS | Compliance | Written confirmation |

**Rollback point:** Can restore access within 2 hours if needed.

### Phase 3: Data Archival (Weeks 9-14)

**Objective:** Archive all historical data to long-term storage for regulatory retention.

| Week | Action | Responsible | Verification |
|------|--------|-------------|-------------|
| W9-W10 | Export full database to Parquet format on S3 | Data Engineering | Row count reconciliation |
| W9-W10 | Export as Oracle Data Pump (.dmp) backup | Oracle DBA Team | Backup integrity verified |
| W11 | Copy archive to S3 Glacier Deep Archive | Cloud Engineering | Lifecycle policy confirmed |
| W11 | Apply S3 Object Lock (Governance mode, 7-year retention) | Cloud Engineering | Lock verification |
| W12 | Verify archive integrity (checksum validation) | Data Engineering | All checksums match |
| W12 | Register archive in OpenMetadata (lineage, retention) | Data Governance | Catalog entries created |
| W13 | Document archive access procedures | Data Engineering | Runbook created |
| W13 | Test archive retrieval (restore random sample) | Data Engineering | Successful retrieval |
| W14 | Archive sign-off by Compliance and Audit | Compliance + Audit | Formal sign-off |

**Archive Specification:**

| Property | Value |
|----------|-------|
| Format (primary) | Apache Parquet (ZSTD compressed) |
| Format (backup) | Oracle Data Pump (.dmp) |
| Storage class | S3 Glacier Deep Archive |
| Encryption | AES-256 (KMS key: alias/atlas-archive) |
| Retention lock | S3 Object Lock, Governance mode, 7 years |
| Location | s3://atlas-archive-prod-eu-west-2/oracle-dwh/ |
| Total estimated size | ~45 TB (compressed) |
| Retrieval SLA | 48 hours (Glacier Deep Archive restore time) |

### Phase 4: Infrastructure Shutdown (Weeks 15-18)

**Objective:** Shut down all Oracle DWH infrastructure components.

| Week | Action | Responsible | Verification |
|------|--------|-------------|-------------|
| W15 | Shutdown OBIEE and WebLogic servers | Middleware Team | Services stopped, ports closed |
| W15 | Shutdown ODI agents and repository | ETL Team | All agents stopped |
| W16 | Shutdown Oracle RAC cluster (all nodes) | Oracle DBA Team | Database DOWN, listener stopped |
| W16 | Shutdown GoldenGate infrastructure | Oracle DBA Team | All processes terminated |
| W17 | Disconnect storage (Exadata, NetApp shelves) | Storage Team | LUNs deprovisioned |
| W17 | Remove network configuration (VLAN 420, 421) | Network Team | VLANs deleted, ACLs removed |
| W18 | Power down physical servers | Data Centre Ops | Servers powered off |
| W18 | Remove servers from monitoring (Nagios, SCOM) | Monitoring Team | No stale alerts |

**No rollback beyond this point** — reinstatement would require full rebuild.

### Phase 5: Decommission Completion (Weeks 19-22)

**Objective:** Complete administrative and commercial decommission activities.

| Week | Action | Responsible | Verification |
|------|--------|-------------|-------------|
| W19 | Terminate Oracle Database Enterprise Edition licences | Procurement | Termination confirmation |
| W19 | Terminate Oracle GoldenGate licences | Procurement | Termination confirmation |
| W19 | Terminate Oracle Data Integrator licences | Procurement | Termination confirmation |
| W19 | Terminate Oracle BI Enterprise Edition licences | Procurement | Termination confirmation |
| W20 | Terminate Oracle Support contract | Procurement | Contract end confirmation |
| W20 | Return/recycle physical hardware | Data Centre Ops | Asset register updated |
| W20 | Secure data destruction on decommissioned disks | Security Team | Destruction certificates |
| W21 | Update CMDB — mark all CIs as Retired | ITSM | CMDB audit clean |
| W21 | Update network documentation | Network Team | Documentation updated |
| W22 | Final decommission report | Programme Manager | Stakeholder distribution |
| W22 | Financial reconciliation (cost savings realised) | Finance | Budget update |

---

## 4. Data Archival Strategy

### 4.1 Retention Requirements

| Data Category | Regulatory Basis | Retention Period | Archive Location |
|-------------|------------------|-----------------|-----------------|
| Financial transactions | Companies Act 2006 s.388; FCA SYSC 9 | 7 years from transaction date | S3 Glacier Deep Archive |
| Customer records (active) | Already in ATLAS — no Oracle archive needed | N/A | ATLAS Lakehouse |
| Customer records (closed) | GDPR + FCA SYSC 9 | 6 years from account closure | S3 Glacier Deep Archive |
| AML/KYC records | MLR 2017 reg.40 | 5 years from end of relationship | S3 Glacier Deep Archive |
| Regulatory reports (generated) | FCA SUP 15 | 7 years | S3 Glacier Deep Archive |
| Audit trails | FCA SYSC 9 | 7 years | S3 Glacier Deep Archive |
| Market data | MiFID II RTS 25 | 7 years | S3 Glacier Deep Archive |
| ETL job logs | Internal policy | 3 years | S3 Standard -> Glacier |

### 4.2 Archive Access Model

Post-decommission, archived Oracle data is accessible via:

1. **Trino (ad-hoc):** Query Parquet archives directly via Iceberg/Hive connector on S3
2. **Automated retrieval:** Lambda function triggers Glacier restore, makes available within 48 hours
3. **DSAR compliance:** Automated extract from archive for data subject access requests
4. **Regulatory request:** Manual retrieval by Data Engineering team (SLA: 5 business days)
5. **Oracle Data Pump (fallback):** If Parquet archive insufficient, restore .dmp to temporary Oracle instance

### 4.3 Archive Testing

| Test | Frequency | Owner |
|------|-----------|-------|
| Random sample retrieval and validation | Quarterly (first year), annually thereafter | Data Engineering |
| DSAR process test using archived data | Annually | DPO Office |
| Regulatory query simulation | Annually | Compliance |
| Archive integrity check (checksums) | Annually | Data Engineering |

---

## 5. License Termination Timeline

### 5.1 Oracle License Inventory

| Product | License Type | Qty | Annual Cost (GBP) | Termination Date |
|---------|-------------|-----|-------------------|-----------------|
| Oracle Database Enterprise Edition | Processor | 16 cores | 780,000 | W19 |
| Oracle Real Application Clusters | Processor | 16 cores | 390,000 | W19 |
| Oracle Partitioning | Processor | 16 cores | 195,000 | W19 |
| Oracle Advanced Compression | Processor | 16 cores | 195,000 | W19 |
| Oracle GoldenGate | Processor | 8 cores | 340,000 | W19 |
| Oracle Data Integrator EE | Processor | 4 cores | 180,000 | W19 |
| Oracle BI Enterprise Edition | Named User Plus | 150 users | 285,000 | W19 |
| Oracle Premier Support | — | — | 435,000 | W20 |
| **Total Annual Savings** | | | **2,800,000** | |

### 5.2 Contract Considerations

| Consideration | Detail | Action Required |
|--------------|--------|-----------------|
| Notice period | 90 days written notice per Oracle contract clause 8.3 | Issue notice at W9 (allows buffer) |
| Support contract | Separate 12-month renewal cycle (April) | Align termination with renewal date or pay early termination |
| Licence perpetuity | Perpetual licences — support termination only stops updates | May retain licences for emergency use (zero ongoing cost) |
| Audit risk | Oracle may audit within 12 months of termination | Ensure compliance documentation ready |
| Hardware disposal | Exadata under finance lease — return at lease end (March 2026) | Coordinate with Finance and vendor |

### 5.3 Cost Savings Realisation

| Period | Savings Type | Amount (GBP) |
|--------|-------------|-------------|
| Year 1 (partial) | Pro-rated licence savings (from W19) | ~1,400,000 |
| Year 1 | Hardware maintenance savings | 180,000 |
| Year 1 | Data centre power/cooling savings | 95,000 |
| Year 2+ (annual) | Full licence savings | 2,800,000 |
| Year 2+ (annual) | Hardware + facilities | 275,000 |
| **Total Year 2+ annual savings** | | **3,075,000** |

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|-----------|-------|
| Undiscovered Oracle dependency post-shutdown | Medium | High | Comprehensive dependency scan (Phase 2); extended read-only period | Application Team |
| Archive retrieval failure | Low | High | Multiple archive formats; quarterly retrieval testing | Data Engineering |
| Regulatory query requiring Oracle-specific format | Low | Medium | Retain Data Pump backups; option to spin up temporary instance | DBA Team |
| Oracle audit triggered by termination | Medium | Medium | Maintain compliance documentation; legal review of termination notice | Procurement + Legal |
| Staff attrition (Oracle DBA skills lost before complete) | Medium | Medium | Document all procedures; complete Phase 3-4 before team transition | HR + DBA Lead |
| Hardware lease complications | Low | Low | Early engagement with leasing company; review contract terms | Finance |
| Data loss during archival | Very Low | Critical | Checksums at every stage; dual-format archive; validate before shutdown | Data Engineering |

---

## 7. Communication Plan

### 7.1 Stakeholder Communications

| Audience | Channel | Timing | Message |
|----------|---------|--------|---------|
| All staff (bank-wide) | Email + Intranet | W1 (read-only), W15 (shutdown) | Service change notification |
| Data consumers | Direct email + Town hall | 4 weeks before each phase | Detailed impact and action required |
| Oracle DBA team | 1:1 meetings + HR | W1 onwards | Career transition support |
| Executive steering | Monthly programme board | Monthly | Progress against plan |
| FCA/PRA | Regulatory notification (if required) | As needed | Material outsourcing change |
| Oracle (vendor) | Formal notice | W9 | Contract termination |
| Finance team | Budget meeting | W1, W19, W22 | Cost savings realisation timeline |
| Audit committee | Quarterly audit committee | Quarterly | Assurance on data archival |

### 7.2 Oracle DBA Team Transition

| Action | Timeline | Owner |
|--------|----------|-------|
| Identify transferable skills (SQL, data modelling, performance tuning) | W1-W2 | HR + DBA Manager |
| Offer retraining programme (AWS, Spark, Trino, dbt) | W3 onwards | L&D + Engineering Manager |
| Internal redeployment opportunities identified | W4-W8 | HR |
| Support transition to ATLAS BAU roles where suitable | W8-W14 | Engineering Manager |
| External placement support (if needed) | W12 onwards | HR |

---

## 8. Governance and Sign-Off

### 8.1 Phase Gate Approvals

Each phase requires formal approval before proceeding:

| Gate | Approvers | Criteria |
|------|-----------|----------|
| Gate 1: Enter Read-Only | Head of Data Eng, Head of Compliance | All prerequisites met |
| Gate 2: Restrict Access | Head of Data Eng, Business Owners | No active consumer dependencies |
| Gate 3: Begin Archival | CTO, Head of Compliance, DPO | Archive strategy approved |
| Gate 4: Shutdown | CTO, CFO, Head of Compliance | Archives validated, no residual risk |
| Gate 5: Licence Termination | CFO, Procurement Director | Contract terms satisfied |
| Gate 6: Decommission Complete | Programme Board | All actions complete, savings realised |

### 8.2 Post-Decommission Obligations

| Obligation | Duration | Owner |
|-----------|----------|-------|
| Maintain access to archived data | 7 years minimum | Data Engineering |
| Respond to regulatory data requests | Indefinite (until retention expires) | Compliance |
| Annual archive integrity verification | 7 years | Data Engineering |
| Retain Oracle expertise (1 person) for emergency | 2 years post-decommission | Engineering Manager |
| Hardware destruction certificates | Retain indefinitely | Security |
