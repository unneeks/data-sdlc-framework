# BAU Handover Plan — Project ATLAS

**Document ID:** ATLAS-TRN-HND-001  
**Version:** 1.0  
**Last Updated:** 2025-06-01  
**Owner:** Programme Manager  
**Classification:** Internal  
**Approved By:** Head of Data Engineering, CTO, COO  

---

## 1. Executive Summary

This document defines the handover process from the Project ATLAS delivery team to the Business-As-Usual (BAU) support organisation. The handover transitions operational ownership of the AWS lakehouse data platform from the project delivery team to the permanent Data Engineering and Platform Operations teams.

### 1.1 Handover Objectives

- Transfer all operational knowledge required to run, maintain, and evolve the ATLAS platform
- Ensure BAU teams can independently resolve issues without project team involvement
- Establish clear accountability boundaries between Build and Run
- Achieve formal sign-off from BAU teams confirming readiness to assume ownership
- Maintain regulatory compliance throughout the transition period

### 1.2 Handover Timeline

| Phase | Duration | Dates | Description |
|-------|----------|-------|-------------|
| Phase 1: Preparation | 4 weeks | W1-W4 | Documentation, knowledge capture, BAU team identification |
| Phase 2: Knowledge Transfer | 6 weeks | W5-W10 | Structured KT sessions, shadowing, hands-on exercises |
| Phase 3: Supervised Operation | 4 weeks | W11-W14 | BAU operates with project team in advisory role |
| Phase 4: Independent Operation | 2 weeks | W15-W16 | BAU operates independently, project team on standby |
| Phase 5: Formal Handover | 1 week | W17 | Sign-off, project team stands down |

---

## 2. Stakeholders and Roles

### 2.1 Handover Governance

| Role | Name/Team | Responsibility |
|------|-----------|---------------|
| Handover Sponsor | Head of Data Engineering | Approves readiness, resolves blockers |
| Handover Lead | Programme Manager | Coordinates handover activities |
| Project Tech Lead | Senior Data Engineer (Project) | Primary knowledge source |
| BAU Receiving Lead | Senior Data Engineer (BAU) | Ensures BAU team readiness |
| Platform SRE Lead | Platform SRE Manager | Assumes operational ownership |
| Service Manager | IT Service Management | Defines support model integration |

### 2.2 BAU Receiving Teams

| Team | Responsibility | Size |
|------|---------------|------|
| Data Engineering (BAU) | Pipeline development, maintenance, and enhancement | 4 engineers |
| Platform SRE | Infrastructure, monitoring, incident response | 3 engineers |
| Data Governance | Data quality, cataloguing, policy enforcement | 2 analysts |
| BI & Analytics | Dashboard maintenance, report development | 2 analysts |

---

## 3. Knowledge Transfer Programme

### 3.1 KT Session Schedule

#### Week 5-6: Architecture and Design

| Session | Duration | Audience | Delivered By | Materials |
|---------|----------|----------|-------------|-----------|
| Solution Architecture Overview | 4 hours | All BAU teams | Solution Architect | Architecture diagrams, ADRs |
| Data Architecture Deep-Dive | 4 hours | Data Engineering | Data Architect | Logical/physical models, lineage |
| Security Architecture | 3 hours | All + InfoSec | Security Architect | Security design doc, threat model |
| Infrastructure Deep-Dive | 4 hours | Platform SRE | Cloud Engineer | Terraform modules, EKS config |
| Integration Points | 3 hours | Data Engineering + SRE | Integration Lead | API contracts, CDC setup |

#### Week 7-8: Operations and Support

| Session | Duration | Audience | Delivered By | Materials |
|---------|----------|----------|-------------|-----------|
| Monitoring and Alerting | 3 hours | Platform SRE | SRE Lead | Monitoring guide, dashboards |
| Incident Response Procedures | 4 hours | All BAU teams | SRE Lead | Runbooks, escalation matrix |
| Disaster Recovery | 4 hours | Platform SRE + Data Eng | DR Lead | DR plan, drill procedures |
| Deployment Procedures | 3 hours | Data Engineering + SRE | DevOps Lead | CI/CD pipelines, release process |
| Capacity Management | 2 hours | Platform SRE | Cloud Engineer | Scaling policies, cost management |

#### Week 9-10: Domain-Specific Deep-Dives

| Session | Duration | Audience | Delivered By | Materials |
|---------|----------|----------|-------------|-----------|
| Ingestion Pipelines (CDC) | 4 hours | Data Engineering | Pipeline Engineer | Code walkthrough, Debezium config |
| Ingestion Pipelines (Streaming) | 4 hours | Data Engineering | Pipeline Engineer | Spark Streaming code, MSK config |
| dbt Transformations | 4 hours | Data Engineering | Analytics Engineer | dbt project, model documentation |
| Trino Administration | 3 hours | Platform SRE | Platform Engineer | Catalog config, query tuning |
| Data Quality Framework | 3 hours | Data Governance | Quality Lead | Quality checks, remediation |
| Governance & Cataloguing | 3 hours | Data Governance | Governance Lead | OpenMetadata, policies |
| Superset Dashboards | 2 hours | BI & Analytics | BI Developer | Dashboard maintenance guide |

### 3.2 Hands-On Exercises

Each KT session includes practical exercises that BAU teams must complete:

| Exercise | Objective | Pass Criteria |
|----------|-----------|---------------|
| Deploy a new ingestion pipeline | Validate ability to extend the platform | Pipeline runs successfully in dev |
| Respond to a P2 alert | Validate incident response capability | Correct diagnosis and resolution within SLA |
| Perform DR data restore | Validate DR procedure knowledge | Successful table restore from backup |
| Add a new dbt model | Validate transformation development skills | Model passes tests and deploys |
| Investigate data quality issue | Validate quality troubleshooting | Root cause identified and remediated |
| Scale Trino cluster | Validate infrastructure management | Successful scale-out and verification |

### 3.3 Shadowing Schedule

During weeks 9-14, BAU team members shadow project team members:

| BAU Role | Shadows | Duration | Focus |
|----------|---------|----------|-------|
| BAU Data Engineer 1 | Project Pipeline Engineer | 3 weeks | Ingestion pipelines |
| BAU Data Engineer 2 | Project Analytics Engineer | 3 weeks | dbt transformations |
| BAU SRE 1 | Project SRE Lead | 4 weeks | Monitoring, incidents |
| BAU SRE 2 | Project Cloud Engineer | 3 weeks | Infrastructure, deployments |
| BAU Data Governance Analyst | Project Quality Lead | 2 weeks | Quality, cataloguing |

---

## 4. Documentation Checklist

### 4.1 Required Documentation (Must be complete before Phase 4)

| Document | Status | Owner | Location |
|----------|--------|-------|----------|
| Solution Architecture | Complete | Solution Architect | docs/03-architecture/ |
| Data Architecture | Complete | Data Architect | docs/03-architecture/ |
| Physical Data Model | Complete | Data Architect | docs/04-design/ |
| Pipeline Design | Complete | Pipeline Lead | docs/04-design/ |
| Security Design | Complete | Security Architect | docs/04-design/ |
| Development Guide | Complete | Tech Lead | docs/05-development/ |
| Coding Standards | Complete | Tech Lead | docs/05-development/ |
| Test Strategy | Complete | QA Lead | docs/06-testing/ |
| Deployment Guide | Complete | DevOps Lead | docs/08-deployment/ |
| Infrastructure-as-Code Guide | Complete | Cloud Engineer | docs/08-deployment/ |
| Operational Runbook | Complete | SRE Lead | docs/09-operations/ |
| Monitoring Guide | Complete | SRE Lead | docs/09-operations/ |
| Disaster Recovery Plan | Complete | DR Lead | docs/09-operations/ |
| Support Model | Complete | Service Manager | docs/10-transition-to-bau/ |
| Decommission Plan | Complete | Programme Manager | docs/10-transition-to-bau/ |

### 4.2 Operational Documentation (Must be validated during Phase 3)

| Document | Validation Method | Validated By |
|----------|-------------------|-------------|
| Runbooks (all) | Execute during live incident or drill | BAU SRE team |
| DR Procedures | Execute DR drill | BAU SRE + Data Eng |
| Deployment Procedures | Perform production deployment | BAU Data Eng |
| Rollback Procedures | Execute rollback in staging | BAU Data Eng |
| Escalation Matrix | Tabletop exercise | All BAU teams |

---

## 5. Readiness Criteria

### 5.1 Technical Readiness

| Criterion | Measurement | Target | Status |
|-----------|-------------|--------|--------|
| BAU team can deploy to production | Observed deployment | 2 successful deployments | Pending |
| BAU team can resolve P2 incident | Observed resolution | 3 incidents resolved independently | Pending |
| BAU team can perform DR restore | Observed restore | 1 successful restore drill | Pending |
| All runbooks validated | Execution log | 100% validated | Pending |
| All KT sessions completed | Attendance register | 100% attendance | Pending |
| Hands-on exercises passed | Exercise results | 100% passed | Pending |
| On-call rotation established | PagerDuty config | Active for 2 weeks | Pending |

### 5.2 Organisational Readiness

| Criterion | Measurement | Target | Status |
|-----------|-------------|--------|--------|
| BAU team fully staffed | Headcount | All positions filled | Pending |
| Support model agreed | Signed document | All parties signed | Pending |
| SLAs defined and agreed | SLA document | Approved by stakeholders | Pending |
| Escalation paths tested | Tabletop exercise | Successful execution | Pending |
| Vendor contracts transferred | Contract status | All transferred to BAU | Pending |
| Cost centre assigned | Finance confirmation | Budget allocated | Pending |

### 5.3 Sign-Off Process

Formal handover requires sign-off from all parties:

| Signatory | Confirms | Sign-Off Date |
|-----------|----------|---------------|
| BAU Data Engineering Lead | Technical capability to operate platform | TBD |
| Platform SRE Manager | Operational capability to support platform | TBD |
| Head of Data Engineering | Overall BAU readiness | TBD |
| Service Manager | Support model integration complete | TBD |
| Programme Manager | All handover criteria met | TBD |

---

## 6. Transition Support (Hypercare)

### 6.1 Hypercare Period

Following formal handover, a 4-week hypercare period provides safety net support:

| Week | Project Team Availability | Response Commitment |
|------|--------------------------|-------------------|
| Week 1 (post-handover) | Full availability (on Slack, joinable on-call) | 30-minute response |
| Week 2 | Available during business hours | 2-hour response |
| Week 3 | Available on-request | 4-hour response |
| Week 4 | Final queries only | Next business day |

### 6.2 Hypercare Escalation

During hypercare, BAU teams may escalate to the project team for:

- P1 incidents where root cause is unclear
- Questions about design decisions not covered in documentation
- Edge cases not encountered during KT
- Configuration or tuning guidance

### 6.3 Hypercare Exit Criteria

Hypercare concludes when:

- No P1/P2 escalations to project team for 7 consecutive days
- BAU team confirms confidence to operate independently
- All hypercare queries resolved and documented
- Knowledge base updated with any new learnings

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| BAU team attrition during handover | Medium | High | Ensure knowledge is distributed, not concentrated. Document everything. |
| Insufficient BAU team size | Medium | High | Validate team sizing against operational demands before Phase 4. |
| Knowledge gaps discovered post-handover | High | Medium | Hypercare period. Comprehensive documentation. Recorded KT sessions. |
| New features required during transition | Medium | Medium | Freeze non-essential changes. Pipeline backlog to BAU team. |
| Regulatory change during transition | Low | High | Compliance team monitors; project team supports if within hypercare. |

---

## 8. Success Metrics

| Metric | Target | Measurement Period |
|--------|--------|-------------------|
| Mean Time to Resolve (P1) | < 1 hour | First 3 months post-handover |
| Mean Time to Resolve (P2) | < 4 hours | First 3 months post-handover |
| Escalation rate to project team | < 5% of incidents | During hypercare |
| SLA adherence | >= 99.5% | First 3 months post-handover |
| Team confidence score | >= 4/5 | Survey at end of hypercare |
| Zero regulatory breaches | 0 | Ongoing |
