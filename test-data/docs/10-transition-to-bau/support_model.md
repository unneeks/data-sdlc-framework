# Support Model — Project ATLAS

**Document ID:** ATLAS-TRN-SUP-001  
**Version:** 1.1  
**Last Updated:** 2025-06-10  
**Owner:** IT Service Management  
**Classification:** Internal  
**Approved By:** Head of Data Engineering, Head of IT Service Management  

---

## 1. Overview

This document defines the BAU support model for the ATLAS data platform following handover from the project delivery team. It establishes the tiered support structure, escalation matrix, SLA targets, and on-call rotation to ensure the platform meets its operational resilience obligations under FCA PS21/3 and PRA SS1/21.

---

## 2. Support Tiers

### 2.1 L1 — First-Line Support (Service Desk)

**Team:** Enterprise IT Service Desk  
**Hours:** 24/7/365  
**Staffing:** Shared resource (part of enterprise service desk rotation)

#### Responsibilities

- Receive and log all incidents and service requests via ServiceNow
- Perform initial triage and categorisation
- Execute basic diagnostic runbooks (pre-defined decision trees)
- Resolve known issues using Knowledge Base articles
- Escalate to L2 when outside documented resolution procedures
- Provide status updates to requestors

#### Capabilities Required

- ServiceNow incident management
- Basic understanding of ATLAS platform components
- Ability to check dashboard health status
- Ability to execute restart procedures for non-critical components
- Ability to verify pipeline status via monitoring dashboards

#### Resolution Scope

| Issue Type | L1 Action | Escalation Trigger |
|-----------|-----------|-------------------|
| Pipeline status enquiry | Check Superset dashboard, report status | N/A |
| Dashboard access request | Process via standard IAM request workflow | If non-standard permissions required |
| Known alert (documented) | Execute runbook steps 1-3 | If steps 1-3 do not resolve |
| Password/access issues | Standard IAM reset procedures | If related to KMS or data classification |
| General enquiries | Knowledge Base lookup | If answer not in KB |

### 2.2 L2 — Second-Line Support (Data Engineering BAU)

**Team:** Data Engineering BAU Team  
**Hours:** Business hours (08:00-18:00 UTC, Mon-Fri) + on-call for P1/P2  
**Staffing:** 4 dedicated engineers (2 pipeline specialists, 1 transformation specialist, 1 serving specialist)

#### Responsibilities

- Investigate and resolve incidents escalated from L1
- Diagnose pipeline failures, data quality issues, and performance problems
- Execute complex runbook procedures
- Perform root cause analysis for recurring issues
- Implement bug fixes and minor enhancements
- Manage scheduled maintenance windows
- Maintain and update operational documentation
- Participate in on-call rotation (out-of-hours P1/P2)

#### Capabilities Required

- Deep knowledge of Spark, Kafka/MSK, Debezium CDC architecture
- dbt development and debugging
- Trino query optimisation and administration
- AWS services: S3, Glue, EKS, MSK, CloudWatch
- Python development for pipeline code
- Terraform for infrastructure changes
- Data quality investigation and remediation

#### Resolution Scope

| Issue Type | L2 Action | Escalation Trigger |
|-----------|-----------|-------------------|
| Pipeline failure | Diagnose root cause, implement fix, redeploy | If infrastructure issue or unknown failure mode |
| Data quality issue | Identify source, apply correction, validate | If requires architectural change |
| Performance degradation | Tune queries, adjust resources, optimise | If requires capacity increase beyond budget |
| Schema change management | Assess impact, implement migration | If affects > 5 downstream consumers |
| Monitoring gap | Add alerting/dashboard coverage | If requires new tooling |
| Minor enhancement | Implement, test, deploy | If effort > 5 days or requires design change |

### 2.3 L3 — Third-Line Support (Platform SRE + Specialists)

**Team:** Platform SRE Team + Domain Specialists  
**Hours:** Business hours + on-call for P1  
**Staffing:** 3 SRE engineers + access to specialist pools

#### Responsibilities

- Resolve complex infrastructure issues
- Manage platform upgrades (EKS, Trino, Spark versions)
- Handle security incidents and vulnerabilities
- Execute disaster recovery procedures
- Manage capacity planning and scaling events
- Resolve cross-team integration issues
- Provide deep technical expertise for novel problems
- Engage AWS Enterprise Support when needed

#### Capabilities Required

- Expert-level Kubernetes/EKS administration
- Network engineering (VPC, security groups, NLB)
- Deep AWS service knowledge (IAM, KMS, networking)
- Security incident response
- Performance engineering and profiling
- Capacity modelling and forecasting
- Vendor management (AWS Support escalation)

#### Resolution Scope

| Issue Type | L3 Action | Escalation Trigger |
|-----------|-----------|-------------------|
| Infrastructure failure | Diagnose and resolve, engage AWS if needed | If AWS service issue requiring AWS resolution |
| Security incident | Contain, investigate, remediate | Automatic CISO notification for all security incidents |
| Platform upgrade | Plan, test, execute rolling upgrade | If upgrade requires downtime > maintenance window |
| Capacity issue | Scale infrastructure, update auto-scaling | If cost increase requires budget approval |
| Novel/unknown failure | Deep investigation, engage specialists | If unresolvable within 4 hours |
| Cross-system integration | Coordinate with upstream/downstream teams | If requires changes to external systems |

### 2.4 Specialist Pools (On-Demand)

| Specialist Area | Team | Engagement Criteria |
|----------------|------|-------------------|
| Data Governance | Data Governance Office | Policy violations, classification issues |
| Security | Information Security | Security incidents, access control issues |
| Compliance | Compliance Team | Regulatory reporting failures, audit queries |
| Network | Network Engineering | Connectivity issues, VPC/routing problems |
| Database | DBA Team | Glue Catalog issues, metadata corruption |
| Vendor (AWS) | AWS Enterprise Support | AWS service issues, quota increases |

---

## 3. Escalation Matrix

### 3.1 Technical Escalation

```
L1 (Service Desk)
    |
    | [Cannot resolve using KB / Runbook steps 1-3]
    v
L2 (Data Engineering BAU)
    |
    | [Infrastructure issue / Novel failure / Security concern]
    v
L3 (Platform SRE)
    |
    | [Requires vendor support / Architectural decision]
    v
AWS Enterprise Support / Architecture Review Board
```

### 3.2 Management Escalation

| Elapsed Time (P1) | Escalation To | Action |
|-------------------|---------------|--------|
| 0 min | L2 On-Call Engineer | Investigate and resolve |
| 30 min | L2 Team Lead | Assess, add resources if needed |
| 1 hour | L3 SRE + Engineering Manager | Cross-team coordination |
| 2 hours | Head of Data Engineering | Executive decision-making |
| 4 hours | CTO + Compliance | Regulatory impact assessment |

| Elapsed Time (P2) | Escalation To | Action |
|-------------------|---------------|--------|
| 0 min | L2 On-Call Engineer | Investigate and resolve |
| 2 hours | L2 Team Lead | Assess and re-prioritise |
| 4 hours | Engineering Manager | Resource allocation |
| 8 hours | Head of Data Engineering | Priority decision |

### 3.3 Regulatory Escalation

| Trigger | Escalation Path | Timeline |
|---------|----------------|----------|
| Regulatory feed at risk | L2 -> Compliance -> Head of Regulatory Reporting | Immediately upon detection |
| Data breach (PII) | L3 -> CISO -> DPO -> ICO notification | 72 hours to ICO |
| FCA/PRA reporting failure | L2 -> Compliance -> Head of Regulatory Reporting -> FCA | Per FCA SUP 15.3 |
| Operational resilience breach | L3 -> Risk -> COO -> FCA/PRA | Per PS21/3 requirements |

---

## 4. SLA Targets

### 4.1 Incident Response SLAs

| Priority | Description | Response Time | Resolution Target | Update Frequency |
|----------|-------------|---------------|-------------------|-----------------|
| P1 — Critical | Complete outage of Tier 1 pipelines; regulatory feed at risk; data loss | 15 minutes | 1 hour | Every 15 minutes |
| P2 — High | Significant degradation; SLA breach imminent; Tier 1 data quality failure | 30 minutes | 4 hours | Every 30 minutes |
| P3 — Medium | Single pipeline failure (non-Tier 1); performance degradation; minor quality issue | 2 hours | 8 business hours | Every 2 hours |
| P4 — Low | Cosmetic issue; enhancement request; documentation update needed | 8 business hours | 5 business days | On resolution |

### 4.2 Service Request SLAs

| Request Type | Response Time | Fulfilment Time |
|-------------|---------------|-----------------|
| New data access request | 4 business hours | 2 business days |
| New dashboard/report | 4 business hours | 10 business days |
| Pipeline modification (minor) | 4 business hours | 5 business days |
| New pipeline (standard) | 1 business day | 15 business days |
| Infrastructure change | 1 business day | 10 business days |

### 4.3 Availability SLAs

| Service | Target Availability | Measurement Window | Exclusions |
|---------|--------------------|--------------------|-----------|
| Streaming Ingestion | 99.9% | Monthly | Planned maintenance windows |
| Batch Ingestion | 99.5% | Monthly | Planned maintenance windows |
| Transformation (dbt) | 99.5% | Monthly | Planned maintenance windows |
| Trino Query Service | 99.9% | Monthly | Planned maintenance windows |
| Superset Dashboards | 99.5% | Monthly | Planned maintenance windows |
| Monitoring & Alerting | 99.99% | Monthly | None |

### 4.4 SLA Reporting

- **Monthly SLA Report:** Produced by L2 team, reviewed by Engineering Manager
- **Quarterly Service Review:** Presented to Head of Data Engineering and business stakeholders
- **Annual Service Improvement Plan:** Based on SLA trends, incident analysis, and feedback
- **Breach Notification:** Any SLA breach triggers automatic notification to Engineering Manager

---

## 5. On-Call Rotation

### 5.1 Rotation Structure

| Rotation | Team | Coverage | Escalation After |
|----------|------|----------|-----------------|
| Primary On-Call | L2 Data Engineering (4 engineers) | 24/7 for P1/P2 | 30 minutes |
| Secondary On-Call | L3 Platform SRE (3 engineers) | 24/7 for P1 | 1 hour |
| Management | Engineering Manager | 24/7 for P1 (escalation only) | 2 hours |

### 5.2 Rotation Schedule

- **Rotation period:** 1 week (Monday 09:00 UTC to Monday 09:00 UTC)
- **Handover:** Written handover in Slack #atlas-oncall at rotation start
- **Maximum consecutive on-call days:** 7 (no back-to-back weeks)
- **Minimum rest between on-call shifts:** 2 weeks
- **Holiday coverage:** Agreed 4 weeks in advance; swap requests via PagerDuty

### 5.3 On-Call Expectations

| Requirement | Target |
|-------------|--------|
| Acknowledge P1 alert | Within 5 minutes |
| Acknowledge P2 alert | Within 15 minutes |
| Begin investigation | Within 15 minutes of acknowledgement |
| Escalate if unable to resolve | Within 30 minutes (P1), 1 hour (P2) |
| Post-incident update | Within 1 hour of resolution |
| Internet connectivity | Required at all times during on-call |
| Laptop availability | Required at all times during on-call |
| Sobriety | Required at all times during on-call |

### 5.4 On-Call Compensation

Per company policy and UK Working Time Regulations:

- On-call allowance: Per HR Policy HR-OC-001
- Callout payment: Per HR Policy HR-OC-001
- Time off in lieu: If called out between 22:00-06:00, minimum 4 hours TOIL next day
- Rest breaks: Compliant with Working Time Regulations 1998

### 5.5 On-Call Tooling

| Tool | Purpose | Access |
|------|---------|--------|
| PagerDuty | Alert routing, escalation, scheduling | All on-call engineers |
| Slack (#atlas-incidents) | Real-time collaboration | All engineering |
| AWS Console | Infrastructure investigation | Role-based (elevated for on-call) |
| Superset Dashboards | Health monitoring | All engineering |
| ServiceNow | Incident logging and tracking | All engineering |
| Runbook Repository | Documented procedures | Git (docs/09-operations/) |

---

## 6. Continuous Improvement

### 6.1 Incident Review

- **Post-Incident Review (PIR):** Required for all P1 and P2 incidents within 5 business days
- **Blameless culture:** Focus on systemic improvements, not individual fault
- **Action tracking:** All PIR actions logged in JIRA, reviewed weekly
- **Trend analysis:** Monthly review of incident patterns and repeat offenders

### 6.2 Service Improvement

| Activity | Frequency | Owner | Output |
|----------|-----------|-------|--------|
| Incident trend analysis | Monthly | L2 Team Lead | Improvement backlog items |
| Knowledge Base review | Monthly | L1 Lead + L2 Team Lead | Updated KB articles |
| Runbook validation | Quarterly | L2 Team | Updated runbooks |
| SLA review | Quarterly | Service Manager | SLA adjustment proposals |
| Support model review | Annually | Head of Data Engineering | Updated support model |
| Tooling assessment | Annually | Platform SRE Lead | Tooling roadmap |

### 6.3 Knowledge Management

- **Knowledge Base:** Confluence space maintained by L2 team
- **Runbooks:** Git-managed (docs/09-operations/runbook.md)
- **Post-Incident Reviews:** Stored in Confluence with linked JIRA actions
- **Lessons Learned:** Quarterly lessons-learned sessions with all support tiers
- **New Joiner Onboarding:** 2-week structured onboarding programme for new team members
