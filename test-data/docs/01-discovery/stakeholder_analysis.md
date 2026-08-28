# Stakeholder Analysis

## Project: ATLAS — Banking Data Platform Migration

### Stakeholder Map

| Stakeholder | Role | Interest | Influence | Engagement Strategy |
|-------------|------|----------|-----------|-------------------|
| Chief Data Officer | Sponsor | Very High | Very High | Weekly steering, final escalation point |
| CTO | Technical Governance | High | Very High | Architecture Review Board participation |
| Head of Risk | Consumer (Risk Models) | Very High | High | Monthly domain review, UAT sign-off |
| Head of Regulatory Reporting | Consumer (Reg Reports) | Very High | High | Weekly checkpoint, regression validation |
| Head of Finance | Consumer (Financial Reports) | High | Medium | Quarterly business review |
| Data Protection Officer | Compliance | High | High | Privacy impact assessment, DPIA review |
| CISO | Security Governance | Medium | High | Security design review, pen test sign-off |
| Internal Audit | Assurance | Medium | High | Audit evidence collection, SOX controls |
| Platform Engineering | Delivery Team | Very High | Medium | Daily standups, sprint ceremonies |
| Data Engineering | Delivery Team | Very High | Medium | Hands-on development, code reviews |
| Change Advisory Board | Release Governance | Low | Very High | Change request approval for production |
| End Users (Analysts) | Consumers | High | Low | UAT participation, training sessions |

### RACI Matrix (Key Activities)

| Activity | CDO | CTO | Platform Eng | Data Eng | Risk | Reg Reporting | Security |
|----------|-----|-----|-------------|----------|------|---------------|----------|
| Business Case Approval | A | C | I | I | C | C | I |
| Architecture Decision | C | A | R | C | I | I | C |
| Data Model Design | I | C | C | R | C | C | I |
| Security Design | I | C | C | R | I | I | A |
| Pipeline Development | I | I | C | R | I | I | I |
| Data Reconciliation | C | I | C | R | A | A | I |
| Go-Live Decision | A | C | R | C | C | C | C |
| BAU Handover | A | I | R | R | C | C | I |

*R = Responsible, A = Accountable, C = Consulted, I = Informed*

### Communication Plan

| Audience | Channel | Frequency | Content | Owner |
|----------|---------|-----------|---------|-------|
| Steering Committee | Face-to-face | Fortnightly | RAG status, risks, decisions needed | Delivery Lead |
| Extended Stakeholders | Email digest | Weekly | Progress summary, upcoming milestones | PMO |
| Delivery Team | Standup | Daily | Blockers, WIP, handoffs | Scrum Master |
| Business Users | Town Hall | Monthly | Demo of new capabilities, timeline | Product Owner |
| Regulators (FCA/PRA) | Formal letter | As needed | Material change notification | Compliance |
| Internal Audit | Audit pack | Quarterly | Control evidence, exceptions | Delivery Lead |

### Stakeholder Concerns & Responses

**Head of Risk:**
- Concern: "Will risk model outputs be identical post-migration?"
- Response: Bit-for-bit reconciliation of all risk scores for 90-day parallel run. Tolerance: zero variance on regulatory capital figures.

**Head of Regulatory Reporting:**
- Concern: "Can we guarantee Basel III report submission deadlines during migration?"
- Response: Phased approach — regulatory domain migrated last, with 6-week dual-run overlap. Rollback plan to Oracle within 4 hours.

**CISO:**
- Concern: "How is PII protected in the lakehouse?"
- Response: Column-level encryption (AWS KMS), row-level security in Trino, data masking for non-prod. Full DPIA submitted.

**Internal Audit:**
- Concern: "How do we maintain SOX ITGC compliance during transition?"
- Response: Dual control framework active during migration. All access provisioning, change management, and data lineage preserved. Automated evidence collection via OpenMetadata.

### Escalation Path

```
Level 1: Delivery Lead → resolves within team (< 24h)
Level 2: Programme Manager → cross-team coordination (< 48h)
Level 3: CDO → strategic/budget decisions (< 1 week)
Level 4: ExCo → regulatory/reputational risk (immediate)
```
