# MASTER MVP BUILD PROMPT

## Agentic Data Engineering Digital Twin & Continuous Delivery Platform

You are a Principal Software Architect, AI Agent Platform Engineer, Data Engineering Architect, and UX/Product Designer.

Build a polished, runnable **MVP prototype** of an enterprise platform called:

# Agentic Data Engineering Engineering System

The platform demonstrates how an existing brownfield data engineering project can be assimilated into a **Digital Engineering Twin**, how an agent ecosystem can be composed around it using a marketplace of agents and skills, how that ecosystem can be evaluated and governed, and how it subsequently operates continuously against changes in the project.

This is a **prototype for executive/product demonstration**, but the architecture must be credible enough that it could evolve into a production platform.

The prototype must prioritize:

1. Complete end-to-end workflow
2. Excellent intuitive UI
3. Strong metamodel
4. Technical + delivery digital twin
5. Agent/skill/tool marketplace
6. Evaluation and trust
7. Human approval gates
8. Brownfield continuous-change workflow
9. Evidence and traceability
10. Agent lifecycle and improvement

Do NOT build a generic chatbot.

Do NOT build merely an "AI agent builder."

The central object is the **Digital Engineering Twin**.

---

# 1. THE CORE PRODUCT CONCEPT

The system must demonstrate this lifecycle:

```text
Existing Data Engineering Project
             ↓
        ASSIMILATION
             ↓
      DIGITAL ENGINEERING TWIN
             ↓
    DELIVERY TYPE RECOGNITION
             ↓
     DELIVERY BLUEPRINT
             ↓
       DELIVERY PLAN
             ↓
    CAPABILITY + GAP ANALYSIS
             ↓
      AGENT COMPOSITION
             ↓
     EVALUATION / CERTIFICATION
             ↓
          DEPLOY
             ↓
     CONTINUOUS OPERATION
             ↓
        CHANGE DETECTED
             ↓
 DELIVERY TYPE CHANGE CLASSIFICATION
             ↓
  TECHNICAL + DELIVERY IMPACT
             ↓
       TEST / VALIDATION
             ↓
        EVIDENCE
             ↓
       APPROVAL GATE
             ↓
          DELIVER
             ↓
      OBSERVE / LEARN
             ↓
          IMPROVE
```

The final demonstration should make this concept visually obvious.

---

# 2. IMPORTANT DISTINCTION

The platform must model BOTH:

## A. Technical Reality

```text
Code
Repositories
Pipelines
Data Assets
Schemas
Lineage
Infrastructure
Tests
Deployments
Dependencies
Architecture
Incidents
Changes
```

AND:

## B. Delivery Reality

```text
Delivery Types
Delivery Blueprints
Delivery Plans
Phases
Tasks
Activities
Inputs
Outputs
Checklists
Acceptance Criteria
Artifacts
Roles
Standards
Policies
Approval Gates
Approvers
Evidence
Definition of Done
Release Process
Change Process
```

These two dimensions form a single Project Digital Twin.

```text
                 PROJECT DIGITAL TWIN
                         │
          ┌──────────────┴──────────────┐
          │                             │
   TECHNICAL TWIN                 DELIVERY TWIN
          │                             │
 Code / Data / Infra          Delivery Types / Blueprints
 Pipelines / Tests            Phases / Tasks / Gates
 Architecture                Inputs / Outputs / Contracts
 Lineage                     Evidence / Standards
          │                             │
          └──────────────┬──────────────┘
                         │
                  PROJECT GRAPH
```

### KEY ARCHITECTURAL HIERARCHY

The agent ecosystem is derived directly from the organization's delivery intent and methodology:

```text
DELIVERY TYPE
      │
      ▼
DELIVERY BLUEPRINT
      │
      ▼
DELIVERY PLAN
      │
      ├── Phases
      ├── Tasks
      ├── Artifacts
      ├── Checklists
      ├── Gates
      └── Evidence
               │
               ▼
       REQUIRED CAPABILITIES
               │
               ▼
       ENGINEERING ROLES
               │
               ▼
             AGENTS
               │
               ▼
            SKILLS
               │
               ▼
             TOOLS
```

---

# 3. MVP DEMONSTRATION SCENARIO

Use one realistic synthetic brownfield project:

# Customer 360 Data Platform

Technology landscape:

```text
SAP
Oracle
Salesforce
    │
    ▼
Pub/Sub
    │
    ▼
Dataflow
    │
    ▼
BigQuery
    │
    ├── dbt
    ├── Dataplex
    └── Airflow
          │
          ▼
     Customer 360
```

Repository:

```text
customer-360-data-platform
```

The prototype should contain synthetic but realistic project artifacts representing:

```text
40+ pipelines
100+ data assets
10+ dbt models
8 orchestration workflows
30+ tests
Terraform configuration
SQL
Python
YAML
Architecture documentation
Delivery methodology
Testing standards
Checklists
Approval gates
Release process
```

The numbers may be simulated.

The user must feel that the platform has inherited an existing enterprise project rather than created a greenfield demo.

---

# 4. TECHNOLOGY STACK

Use:

```text
Frontend:
React
TypeScript

Backend:
Python
FastAPI

Database:
PostgreSQL

Graph:
Neo4j

Background jobs:
Python workers

Styling:
Modern enterprise UI framework / Tailwind

Charts:
Recharts or equivalent

Graph visualization:
React Flow, Cytoscape.js, or equivalent

Containerization:
Docker Compose

Testing:
pytest
Vitest / Playwright
```

Use an LLM abstraction layer.

The system must not be tightly coupled to one LLM provider.

For the MVP, deterministic/mock agent execution is acceptable and encouraged where it improves demo reliability.

The UI should not reveal which operations are simulated.

---

# 5. REPOSITORY STRUCTURE

Create:

```text
agentic-data-engineering/
│
├── apps/
│   ├── web/
│   ├── api/
│   └── worker/
│
├── domain/
│   ├── metamodel/
│   ├── projects/
│   ├── delivery/
│   ├── capabilities/
│   ├── roles/
│   ├── agents/
│   ├── skills/
│   ├── tools/
│   ├── knowledge/
│   ├── policies/
│   ├── workflows/
│   ├── evaluations/
│   └── evidence/
│
├── marketplace/
│   ├── roles/
│   ├── agents/
│   ├── skills/
│   ├── tools/
│   ├── knowledge/
│   ├── policies/
│   └── evaluations/
│
├── demo/
│   ├── project/
│   ├── documentation/
│   ├── delivery-model/
│   ├── changes/
│   └── scenarios/
│
├── adapters/
│
├── tests/
│
├── docs/
│
└── docker-compose.yml
```

---

# 6. CORE METAMODEL

Implement these entities:

```text
Project
Problem
Requirement

DataAsset
Pipeline
Schema
Lineage
Repository
CodeArtifact
InfrastructureResource
Test
Deployment
Change
Incident

DeliveryType
DeliveryBlueprint
DeliveryPlan
DeliveryModel
DeliveryPhase
DeliveryTask
DeliveryActivity
DeliveryInput
DeliveryOutput
DeliveryArtifact
Checklist
ChecklistItem
AcceptanceCriterion
ApprovalGate
ApprovalRule
Approval
DeliveryRole
Standard
Template
DefinitionOfDone

Capability
DeliveryCapability
EngineeringRole

Agent
AgentVersion
Skill
Tool
KnowledgePack
Policy
Workflow

EvaluationSuite
EvaluationScenario
EvaluationResult
Evidence
Finding
Recommendation

Observation
Decision
Memory
```

---

# 7. CRITICAL RELATIONSHIPS

Implement graph relationships such as:

```text
Project
  HAS_ACTIVE_PLAN → DeliveryPlan

DeliveryPlan
  INSTANTIATED_FROM → DeliveryBlueprint

DeliveryBlueprint
  IMPLEMENTS → DeliveryType

DeliveryBlueprint
  CONTAINS → DeliveryPhase

DeliveryType
  REQUIRES_CAPABILITY → Capability

DeliveryType
  GOVERNED_BY → Policy

DeliveryType
  REQUIRES_GATE → ApprovalGate

Project
  CONTAINS → DataAsset

Project
  CONTAINS → Pipeline

Pipeline
  DEPENDS_ON → DataAsset

DataAsset
  HAS_LINEAGE_TO → DataAsset

Change
  IMPACTS → Pipeline

Change
  IMPACTS → DataAsset

Change
  IMPACTS → DeliveryTask

Change
  IMPACTS → ApprovalGate

Capability
  REALIZED_BY → EngineeringRole

EngineeringRole
  IMPLEMENTED_BY → Agent

Agent
  HAS_VERSION → AgentVersion

Agent
  USES → Skill

Agent
  USES → Tool

Agent
  CONSUMES → KnowledgePack

Agent
  GOVERNED_BY → Policy

Agent
  EVALUATED_BY → EvaluationSuite

DeliveryPhase
  CONTAINS → DeliveryTask

DeliveryTask
  REQUIRES → DeliveryInput

DeliveryTask
  PRODUCES → DeliveryOutput

DeliveryTask
  HAS_CHECKLIST → Checklist

DeliveryTask
  REQUIRES_GATE → ApprovalGate

Task
  PRODUCES → Evidence

ApprovalGate
  REQUIRES → Evidence

ApprovalGate
  PRODUCES → Approval

Evaluation
  PRODUCES → Evidence

Recommendation
  SUPPORTED_BY → Evidence
```

All important relationships should carry provenance where appropriate:

```text
confidence
source
discovered_at
discovered_by
verification_status
```

---

# 8. DELIVERY DIGITAL TWIN

This is a critical part of the MVP.

The system must not treat project documentation merely as text.

It must extract structured delivery metadata.

For example, from:

> "Architecture review must be completed before development begins. The solution architect approves the architecture document."

derive:

```text
Phase:
Architecture

Task:
Architecture Review

Artifact:
Architecture Document

Role:
Solution Architect

Gate:
Architecture Approval

Precondition:
Before Development

Action:
Approve
```

Maintain:

```text
source document
section/page
confidence
extraction timestamp
```

Use:

```text
OBSERVED
INFERRED
HUMAN_VERIFIED
CERTIFIED
```

to distinguish certainty.

---

# 9. DELIVERY MODEL

Seed the demo project with:

```text
Discovery
Requirements
Architecture
Design
Development
Testing
Release
Deployment
Operations
```

Each phase should have:

```text
Purpose
Tasks
Inputs
Outputs
Roles
Checklists
Acceptance Criteria
Approval Gates
Entry Criteria
Exit Criteria
Policies
Standards
Templates
Evidence Requirements
```

---

# 10. EXAMPLE DELIVERY TASK

Create:

## Create Logical Data Model

```text
Phase:
Design

Inputs:
Business Requirements
Conceptual Model
Enterprise Data Standards

Outputs:
Logical Data Model
Traceability Matrix

Skills:
Logical Modeling
Schema Analysis

Checklist:
12 items

Acceptance Criteria:
8 items

Required Evidence:
Logical Model
Traceability

Approval:
Data Architect
```

The UI must be able to display this as an actual delivery contract.

---

# 11. DELIVERY CONTRACT

Implement:

```text
DeliveryContract
```

A DeliveryContract binds:

```text
Task
Inputs
Outputs
Skills
Tools
Knowledge
Policies
Checklist
Acceptance Criteria
Evidence Requirements
Approval Gate
```

Agents execute against DeliveryContracts.

This is one of the core abstractions of the platform.

---

# 11A. DELIVERY TYPES & DELIVERY BLUEPRINTS CONCEPT

A **Delivery Type** represents the first-class entry point into the organization's delivery methodology.

The system must not compose agents directly from a generic problem statement or prompt. Instead, requests flow through the structured hierarchy:

```text
Business / Engineering Request
            ↓
       Delivery Type
            ↓
    Delivery Blueprint
            ↓
      Delivery Plan
            ↓
      Delivery Phases
            ↓
        Delivery Tasks
            ↓
 Inputs / Outputs / Artifacts
            ↓
 Checklists / Acceptance Criteria
            ↓
      Agents / Skills / Tools
            ↓
       Evaluation Suites
            ↓
       Approval Gates
            ↓
          Delivery
```

### Metamodel Schemas

Implement `DeliveryType`, `DeliveryBlueprint`, and `DeliveryPlan` entities:

#### `delivery_type`
```yaml
delivery_type:
  id:
  name:
  description:
  business_purpose:
  entry_conditions: []
  applicable_project_types: []
  delivery_blueprint:
  phases: []
  required_roles: []
  required_capabilities: []
  required_artifacts: []
  required_checklists: []
  required_evaluations: []
  approval_gates: []
  mandatory_policies: []
  default_agents: []
  optional_agents: []
  risk_profile:
  change_classification:
  lifecycle:
```

#### `delivery_blueprint`
```yaml
delivery_blueprint:
  id:
  delivery_type:
  version:
  phases:
    - id:
      name:
      sequence:
      tasks: []
      required_inputs: []
      expected_outputs: []
      required_agents: []
      optional_agents: []
      checklists: []
      evaluations: []
      gates: []
      entry_criteria: []
      exit_criteria: []
  risk_rules: []
  approval_rules: []
  evidence_requirements: []
```

#### `delivery_plan`
A `DeliveryPlan` is an instantiated `DeliveryBlueprint` for a specific project/change, containing actual Tasks, Agents, Skills, Artifacts, Tests, Checklists, Gates, Evidence, and Approvals.

---

# 11B. INITIAL DELIVERY TYPES CATALOG

The MVP must support at least these 9 initial Delivery Types:

### 1. `DATA_PRODUCT_NEW` (New Data Product)
A completely new data product is being created (e.g., Customer Risk Data Product).
- **Lifecycle**: Idea ➔ Requirements ➔ Discovery ➔ Conceptual Design ➔ Architecture ➔ Logical/Physical Design ➔ Development ➔ Testing ➔ Governance ➔ Operational Readiness ➔ Release ➔ Operate.
- **Deliverables**: Business requirements, Data product definition, Data contract, Conceptual model, Logical model, Architecture, Pipeline design, DQ rules, Security classification, Ownership, Tests, Runbook, Operational readiness evidence.

### 2. `DATA_PRODUCT_AMENDMENT` (Data Product Amendment)
An existing data product is being changed (e.g., Add customer segment attribute, change risk score calculation, modify transformation).
- **Lifecycle**: Existing Data Product ➔ Change Analysis ➔ Technical & Delivery Impact ➔ Determine affected contracts & consumers ➔ Determine required tasks ➔ Regression ➔ Approval ➔ Release.
- **Principle**: Reuses existing artifacts wherever possible rather than recreating them.

### 3. `DATA_PRODUCT_DEFECT` (Defect / Remediation)
An existing product has an issue requiring correction (e.g., Incorrect calculation, DQ failure, broken pipeline, broken lineage).
- **Lifecycle**: Incident / Defect ➔ Root Cause ➔ Impact ➔ Remediation ➔ Regression ➔ Evidence ➔ Approval ➔ Release.

### 4. `DATA_PLATFORM_MIGRATION` (Data Platform / Warehouse Migration)
The primary MVP demonstration scenario (e.g., Legacy DW to Cloud Lakehouse).
- **Lifecycle Activities**: Source Discovery ➔ Dependency Discovery ➔ Migration Assessment ➔ Target Architecture ➔ Source-to-Target Mapping ➔ Transformation Mapping ➔ Data Contract Analysis ➔ Pipeline Migration ➔ Data Reconciliation ➔ Parallel Run ➔ Performance Validation ➔ Consumer Validation ➔ Cutover Planning ➔ Rollback Planning ➔ Cutover ➔ Post-Cutover Validation ➔ Legacy Decommission.

### 5. `NEW_DATA_SOURCE_ONBOARDING` (New Data Source Onboarding)
Onboarding a new source feed (e.g., Salesforce CRM ingestion).
- **Lifecycle**: Source Assessment ➔ Security Assessment ➔ Schema Discovery ➔ Data Contract ➔ Ingestion Design ➔ Pipeline Development ➔ Data Quality ➔ Testing ➔ Governance ➔ Release.

### 6. `DATA_SOURCE_CHANGE` (Data Source Change)
An existing source schema or format changes (e.g., `STATUS CHAR(1)` ➔ `VARCHAR(10)`).
- **Lifecycle**: Schema Impact ➔ Pipeline Impact ➔ Data Contract Impact ➔ Downstream Impact ➔ Test Selection ➔ Delivery Impact ➔ Approval.

### 7. `DATA_PRODUCT_RETIREMENT` (Data Product Retirement)
An existing data product is being decommissioned.
- **Lifecycle**: Retirement Assessment ➔ Consumer Discovery ➔ Dependency Analysis ➔ Migration/Replacement Analysis ➔ Business Approval ➔ Consumer Notification ➔ Decommission ➔ Metadata Update ➔ Evidence.

### 8. `REGULATORY_POLICY_CHANGE` (Regulatory / Policy Change)
A regulatory or enterprise policy change requires engineering modifications (e.g., GDPR retention requirement).
- **Lifecycle**: Policy Change ➔ Affected Assets ➔ Affected Data Products ➔ Affected Pipelines ➔ Compliance Gap ➔ Remediation ➔ Evidence ➔ Compliance Approval.

### 9. `PLATFORM_MODERNIZATION` (Platform Modernization)
Upgrading underlying engineering frameworks (e.g., Legacy ETL ➔ Spark/dbt on Dataflow).
- **Focus**: Engineering-platform modernization distinct from data migration.

---

# 11C. DELIVERY TYPE CLASSIFICATION & HUMAN OVERRIDE

The platform implements an automated **Delivery Type Classifier**.

### Classification Engine
- **Input**: Natural language request, issue ticket, or git commit diff metadata.
- **Output**: Primary & secondary Delivery Type classifications, confidence score (%), and explicit evidence reasoning ("Why was this classified as a Migration?").

Example Output:
```text
Delivery Type: DATA_PLATFORM_MIGRATION
Confidence: 96%

Detected Characteristics:
✓ Existing legacy platform detected (Teradata DW)
✓ New target platform detected (Cloud Lakehouse)
✓ Existing data assets mapped (Customer domain)
✓ Source-to-target data movement required
✓ Ingestion & transformation pipeline changes
✓ Downstream consumer impact identified
```

### Controlled Human Override
Classification is a controlled decision rather than an opaque LLM action. The UI presents:
- `[Accept]` – Confirms classification and instantiates the default Delivery Blueprint.
- `[Change Type]` – Allows user to manually select a different Delivery Type (e.g., override to `DATA_PRODUCT_AMENDMENT`), triggering dynamic recalculation of the Delivery Blueprint.

---

# 11D. MULTI-DELIVERY TYPE COMPOSITION

Real enterprise requests often combine multiple Delivery Types (e.g., *Migrate Customer Risk data product to Lakehouse while simultaneously updating the risk calculation logic*).

### Multi-Type Composition Rules:
```text
Primary:    DATA_PLATFORM_MIGRATION
Secondary:  DATA_PRODUCT_AMENDMENT
     ↓
Migration Blueprint + Amendment Blueprint
     ↓
Combined Delivery Plan
```

### Task & Gate Deduplication:
The composition engine merges the blueprints and automatically deduplicates redundant tasks and gates (e.g., `Regression Testing` or `Security Assessment` are combined and executed once rather than duplicated).

---

# 11E. CONTEXT-AWARE MAPPING & RISK PROFILES

The Delivery Type directly determines the recommended agent workforce, required skills, gates, evidence requirements, and baseline risk.

### Context-Aware Workforces

#### Migration Workforce:
`Migration Architect Agent`, `Source Discovery Agent`, `Dependency Analysis Agent`, `Mapping Agent`, `Pipeline Migration Agent`, `Data Reconciliation Agent`, `Regression Agent`, `Cutover Agent`, `Delivery Compliance Agent`.

#### New Data Product Workforce:
`Requirements Agent`, `Data Product Architect Agent`, `Data Modeling Agent`, `Pipeline Agent`, `Data Contract Agent`, `Data Quality Agent`, `Governance Agent`, `Security Agent`, `Test Agent`, `Operational Readiness Agent`.

#### Amendment Workforce:
`Change Analysis Agent`, `Impact Analysis Agent`, `Data Contract Agent`, `Regression Agent`, `Data Quality Agent`, `Delivery Compliance Agent`.

### Risk Calculation Logic
Each Delivery Type defines a Baseline Risk (`Migration`: HIGH, `New Product`: MEDIUM, `Amendment`: LOW/MEDIUM, `Regulatory`: HIGH). Base risk is modified by project-specific factors:

```text
Final Risk = Base Risk + Data Criticality + Consumer Count + Change Magnitude + Regulatory Sensitivity + Migration Complexity + Rollback Difficulty
```

The resulting risk score determines required agents, evaluation criteria, approval gate stringency, autonomy level, and mandatory evidence.

---

# 11F. DELIVERY TYPE UI & ONBOARDING ENTRY POINT

The onboarding wizard and change entry point begin with:

# What are you delivering?

Interactive UI display cards:

```text
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│ New Data Product   │  │ Amend Data Product │  │ Migrate Platform   │
│ Create something   │  │ Change an existing │  │ Move workloads to  │
│ new                │  │ product            │  │ new architecture   │
└────────────────────┘  └────────────────────┘  └────────────────────┘

┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│ New Data Source    │  │ Fix / Remediate    │  │ Retire / Decouple  │
│ Onboard a new      │  │ resolve an issue   │  │ Decommission a     │
│ source feed        │  │ or defect          │  │ data product       │
└────────────────────┘  └────────────────────┘  └────────────────────┘
```

The selected delivery type determines the delivery blueprint and recommended engineering workforce.

### Delivery Type Comparison UI
The UI allows inspecting the metamodel comparison matrix across types:

```text
Delivery Type Comparison

                   Migration   Amendment   New Product

Phases                 9          5            8
Tasks                  42         18           37
Agents                 10          6           11
Gates                   8          4            7
Evidence               21         10           19
Risk                   High      Medium        Medium
```

### Migration Blueprint Execution UI
For the primary MVP migration scenario, the UI displays the interactive Delivery Plan:

```text
MIGRATION DELIVERY PLAN — Customer Domain Wave

✓ Discovery
✓ Assessment
✓ Target Architecture
● Source-to-Target Mapping
○ Pipeline Migration
○ Data Reconciliation
○ Parallel Run
○ Cutover
○ Decommission
```

Clicking each phase exposes underlying Tasks, Agents, Skills, Artifacts, Tests, Checklists, Gates, and Evidence.

---

# 12. AGENT METAMODEL

An Agent represents an implementation of an EngineeringRole.

Attributes:

```text
id
name
version
description
engineering_role
capabilities
delivery_capabilities
skills
tools
knowledge
policies
supported_phases
supported_tasks
supported_artifacts
supported_gates
inputs
outputs
risk_level
autonomy_level
evaluation_suite
trust_score
certification_status
```

An agent must declare not only:

> "What can I do?"

but:

> "Where in the organization's delivery process can I do it?"

---

# 13. INITIAL AGENT ECOSYSTEM

Seed at least these agents:

### Discovery

```text
Project Discovery Agent
Architecture Discovery Agent
Metadata Discovery Agent
Lineage Discovery Agent
```

### Analysis

```text
Requirements Agent
Impact Analysis Agent
Change Analysis Agent
```

### Architecture

```text
Data Architecture Agent
Logical Modeling Agent
Pipeline Architecture Agent
```

### Testing

```text
Test Strategy Agent
Regression Test Agent
Data Quality Agent
Test Failure Analysis Agent
```

### Governance

```text
Governance Agent
Security Agent
Delivery Compliance Agent
```

### Operations

```text
Observability Agent
Cost Optimization Agent
```

---

# 14. MVP AGENT FOCUS

Do not attempt to make all agents fully autonomous.

Fully demonstrate these four:

```text
Impact Analysis Agent
Regression Test Agent
Data Quality Agent
Delivery Compliance Agent
```

Other agents can have realistic marketplace metadata and simulated execution.

---

# 15. SKILLS

Create a reusable skill catalogue.

Minimum:

```text
repository-scan
architecture-inference
dependency-analysis
lineage-analysis
impact-analysis

requirement-extraction

test-selection
schema-validation
data-quality-validation
source-target-reconciliation
regression-testing
failure-classification
root-cause-analysis

checklist-validation
artifact-completeness
gate-readiness
evidence-validation
delivery-compliance

risk-assessment
documentation-generation
```

Every skill has:

```text
inputs
outputs
preconditions
postconditions
dependencies
required_tools
risk
evaluation_suite
```

---

# 16. TOOLS

Seed:

```text
Git
GitHub
BigQuery
Dataflow
Pub/Sub
Dataplex
dbt
Airflow
Terraform
Neo4j
```

Tool actions must be classified:

```text
READ_ONLY
LOW_RISK_WRITE
HIGH_RISK_WRITE
DESTRUCTIVE
```

For the MVP most actions can be simulated.

---

# 17. MARKETPLACE

Build a marketplace containing:

```text
Engineering Roles
Agents
Skills
Tools
Knowledge Packs
Policies
Evaluation Suites
Workflow Templates
```

The marketplace must be searchable and filterable by:

```text
Capability
Role
Platform
Technology
Risk
Certification
Trust Score
Version
```

Example:

```text
Regression Test Agent v2.1

Role:
Regression Engineer

Capabilities:
Impact Analysis
Regression Testing

Skills:
7

Tools:
GitHub
BigQuery
Neo4j

Trust Score:
94%

Certification:
CERTIFIED

Risk:
Medium
```

---

# 18. CAPABILITY GRAPH

Create a capability model.

Example:

```text
Capability:
Regression Assurance

        ↓

Engineering Roles:
Impact Analysis Engineer
Regression Engineer
Data Quality Engineer

        ↓

Agents

        ↓

Skills

        ↓

Tools
```

Also distinguish:

```text
Technical Capability
Delivery Capability
```

Examples:

Technical:

```text
Streaming
CDC
Data Quality
Lineage
Data Transformation
```

Delivery:

```text
Change Assurance
Architecture Assurance
Release Assurance
Regression Assurance
Operational Readiness
Governance Assurance
```

---

# 19. AGENT COMPOSITION ENGINE

Given:

```text
Project
Technical capabilities
Delivery capabilities
Capability gaps
Technology landscape
Delivery model
Policies
Available marketplace components
```

produce:

```text
Recommended Agent Ecosystem
```

Rank candidate agents using:

```text
Capability fit
Delivery-process fit
Technology compatibility
Evaluation score
Trust
Security
Cost
Risk
Certification
```

Show the user WHY each agent was selected.

---

# 20. BROWNFIELD ASSIMILATION

Create an onboarding wizard.

Stages:

```text
1 CONNECT
2 DISCOVER
3 UNDERSTAND
4 CAPABILITY MAP
5 DELIVERY MODEL
6 GAP ANALYSIS
7 COMPOSE
8 EVALUATE
9 DEPLOY
```

The wizard should appear as a visually compelling progress workflow.

---

# 21. ASSIMILATION SOURCES

For MVP, simulate or ingest:

```text
Git repository
SQL
Python
YAML
Terraform
Markdown
PDF/DOCX delivery documentation
Architecture documents
Testing standards
Checklists
Release process
```

The synthetic demo dataset should contain these artifacts.

---

# 22. PROJECT DIGITAL TWIN UI

Build an interactive graph.

Nodes:

```text
Requirement
Pipeline
Dataset
Table
Code
Test
DeliveryTask
Checklist
Gate
Agent
Skill
Tool
Evidence
Approval
```

Clicking any node opens a right-side inspector.

Example:

```text
customer_360

Owner:
Customer Data Team

Quality:
92%

Lineage:
87%

Upstream:
6

Downstream:
14

Related Delivery Tasks:
3

Related Tests:
8

Related Agents:
2
```

---

# 23. DELIVERY MODEL UI

Create a dedicated view:

```text
Discovery
   ↓
Requirements
   ↓
Architecture
   ↓
Design
   ↓
Development
   ↓
Testing
   ↓
Release
   ↓
Operations
```

Click a phase.

Show:

```text
Tasks
Inputs
Outputs
Agents
Checklists
Evidence
Gates
Approvers
Status
```

---

# 24. CAPABILITY HEALTH UI

Display:

```text
Metadata Management       92%
Pipeline Engineering      97%
Data Quality              64%
Regression Testing        42%
Lineage                   73%
Documentation             51%
Governance                82%
Observability             69%
```

Clicking a capability should show:

```text
Current State
Desired State
Gap
Evidence
Risk
Recommended Roles
Recommended Agents
```

---

# 25. AGENT COMPOSER UI

Show an interactive composition graph:

```text
Regression Assurance
        │
        ├── Impact Analysis Agent
        │        ├── Impact Analysis Skill
        │        └── Dependency Analysis Skill
        │
        ├── Regression Agent
        │        ├── Test Selection
        │        └── Reconciliation
        │
        └── Data Quality Agent
                 └── DQ Validation
```

Allow the user to:

```text
Add Agent
Remove Agent
Replace Agent
Inspect Agent
Compare Agents
View Dependencies
View Evaluation
```

---

# 26. EVALUATION HARNESS

This must be visible and credible.

Every production-capable agent must be evaluated.

Evaluate:

```text
Skill
Agent
Workflow
Agent Ecosystem
```

Dimensions:

```text
Correctness
Completeness
Precision
Recall
False Positive Rate
False Negative Rate
Coverage
Security
Governance
Explainability
Traceability
Human Acceptance
```

For the MVP, use deterministic benchmark scenarios.

---

# 27. CERTIFICATION

Show:

```text
Regression Agent v2.1

Impact Analysis       96% ✓
Test Selection        93% ✓
Reconciliation        91% ✓
Failure Analysis      89% ✓

Security              PASS
Policy Compliance     PASS
Evidence              PASS

Overall Trust Score   94%

CERTIFIED
```

Provide:

```text
View Evaluation
View Evidence
View Limitations
```

Do not expose chain-of-thought.

Expose concise decision summaries and evidence references.

---

# 28. DELIVERY COMPLIANCE EVALUATION

Agents must be evaluated on both:

```text
Technical Performance
+
Delivery Conformance
```

Example:

```text
Technical Accuracy        94%
Impact Detection          92%
Test Selection            96%

Checklist Compliance      100%
Evidence Completeness      95%
Gate Assessment             97%

Overall                    95%
```

An agent that produces technically correct output but ignores mandatory delivery controls must fail certification.

---

# 29. DEPLOYMENT

After certification:

```text
Deploy Agent Ecosystem
```

Show:

```text
12 Agents
27 Skills
10 Tools
8 Knowledge Packs
6 Policies
11 Evaluation Suites

Trust Score:
94%

Automation Level:

Analyse              Automatic
Test Execution       Automatic
Report Generation    Automatic
PR Creation          Automatic
Code Modification    Approval Required
Production Deploy    Approval Required
```

---

# 30. BROWNFIELD CONTROL CENTER

After deployment the onboarding wizard disappears.

The user enters:

# Engineering Control Center

Show:

```text
Project Health
Agent Health
Capability Health
Delivery Readiness
Open Changes
Tests
Quality
Governance
Recent Activity
```

The interface should feel like an operational engineering platform.

---

# 31. SIMULATED CHANGE — THE HERO DEMO

Add a prominent button:

# Simulate Business Change

When clicked, simulate an enterprise change request that instantiates a **Delivery Blueprint** and flows through the complete **Data SDLC Lifecycle**:

> **Primary Scenario**: `Delivery Type: DATA_PLATFORM_MIGRATION` (`Blueprint: DW_TO_LAKEHOUSE_MIGRATION`, Wave: Customer Domain).
> Architectural Change Request (`CR-2026-8942`): Redirection of Source Feeds (Salesforce CRM & SAP Customer Data) from existing Data Warehouse (`dw_staging_db`) to a new Cloud Lakehouse architecture (`lakehouse_raw_db` / Object Storage + BigLake Iceberg tables).

### 1. Primary Migration Blueprint Execution

When triggered, animate the progressive multi-phase blueprint execution flow across both the **Delivery Twin** and **Technical Twin**:

```text
Change Request Ingestion (CR-2026-8942)
       ↓
Delivery Type Classifier: DATA_PLATFORM_MIGRATION (96% Confidence)
       ↓
Delivery Blueprint Instantiated: DW_TO_LAKEHOUSE_MIGRATION v2.1
       ↓
[Phase 1: Architecture & Feasibility Assessment]
       ├── Feasibility Assessment Agent evaluates storage, risk, cost & compatibility
       └── Feasibility Approval Gate evaluated
       ↓
[Phase 2: Data & Schema Design]
       ├── Data Architecture Agent generates Target Lakehouse Logical Model
       └── Source-to-Target Schema Mapping Matrix (`dw_staging` ➔ `lakehouse_raw`)
       ↓
[Phase 3: Technical & Pipeline Design]
       ├── Pipeline Architecture Agent drafts Technical Specifications
       └── Infrastructure Design created (`terraform/lakehouse_ingestion.tf`)
       ↓
[Phase 4: Development & Code Implementation]
       ├── Code Generation Agent updates ingestion pipeline (`salesforce_customer_ingest.py`)
       └── Transformation Model refactored (`stg_lakehouse_customers.sql`)
       ↓
[Phase 5: Testing, Parity & Reconciliation]
       ├── Regression & Data Quality Agents select 10 targeted test suites
       └── Source-to-Target Data Reconciliation & Schema Parity executed
       ↓
[Phase 6: Failure & Root Cause Analysis]
       ├── Reconciliation failure detected (Timestamp format precision drift)
       └── Test Failure Analysis Agent conducts automated RCA
       ↓
[Phase 7: Governance & Delivery Gate]
       ├── Delivery Compliance Agent aggregates evidence across all SDLC phases
       └── Release Readiness Gate status: BLOCKED
       ↓
[Phase 8: Remediation & Resolution]
       └── System proposes fix, updates Lakehouse Runbook & creates PR
```

### 2. Continuous Brownfield Change Mid-Migration

To showcase continuous brownfield delivery, simulate a concurrent source schema change while the migration wave is active:

```text
Simulated Source Change:
SAP Customer Feed: STATUS CHAR(1) ➔ VARCHAR(10)

Classifier Output:
Change Type: SOURCE_SCHEMA_CHANGE

Affected Delivery Types:
✓ DATA_PLATFORM_MIGRATION (Active Migration Wave)
✓ DATA_PRODUCT_AMENDMENT (Customer 360 Data Product)

Combined Delivery Plan Composition:
Migration Blueprint + Amendment Blueprint
     ↓
Merged Plan (Deduplicated Tasks & Gates)
```

This animation progressively demonstrates in the UI how the platform derives the agent workforce from organizational delivery blueprints and dynamically adapts plans when continuous brownfield changes occur.

---

# 32. TECHNICAL IMPACT

Show the complete lineage and technical asset dependency graph resulting from the SDLC design and implementation phases:

```text
CR-2026-8942 Architectural Specification
        │
        ├── [Data Design Spec] lakehouse_customer_schema_mapping.v1.json
        │
        ├── [Technical Design Spec] lakehouse_pipeline_arch_doc.md
        │
        └── [Technical Twin Implementation]
                │
                ├── [Infrastructure] terraform/lakehouse_ingestion.tf
                │
                └── salesforce_customer_ingest.py / sap_orders_ingest.tf
                        │
                        └── [Redirected Sink] dw_staging.customer_events ➔ lakehouse_raw.customer_events
                                │
                                ├── stg_lakehouse_customers.sql (dbt model)
                                ├── customer_profile.sql (dbt model)
                                ├── customer_360.sql (dbt model)
                                └── customer_quality_report.sql (dbt model)
```

Classify technical entities into clear status categories:

```text
Designed         (Schema mapping & technical specification artifacts)
Changed          (Source feed endpoints & Terraform infrastructure config)
Redirected       (Data assets moving from DW tables to Lakehouse storage)
Impacted         (Downstream dbt models, views & Dataflow pipelines)
Tested           (Selected regression & reconciliation tests)
Safe             (Unmodified upstream/independent pipelines)
Risk             (Potential schema drift / format incompatibility)
```

---

# 33. DELIVERY IMPACT

Show how the change propagates across the Delivery Twin phases, tasks, and approval gates:

```text
Affected Delivery Tasks across SDLC Phases

Phase: Architecture
  ✓ Feasibility Assessment & Risk Analysis
  ✓ Architecture Feasibility Sign-off

Phase: Design
  ✓ Target Data & Schema Design
  ✓ Pipeline Technical Specification & Infrastructure Plan

Phase: Development
  ✓ Source Feed Endpoint Modification
  ✓ Infrastructure Provisioning (Terraform Execution Plan)

Phase: Testing
  ✓ Source-to-Target Data Reconciliation
  ⚠ Schema Parity & Format Drift Validation

Phase: Operations & Release
  ⚠ Lakehouse Operational Runbook Update
  ⚠ Release Readiness Gate Sign-off

Affected Approval Gates

✓ Architectural Feasibility Gate
⚠ Security & Governance Gate
⚠ Release Readiness Gate
```

Show required artifacts and compliance status across SDLC phases:

```text
✓ Feasibility & Risk Assessment Report (Architecture Phase)
✓ Target Schema Mapping & Logical Model (Data Design Phase)
✓ Pipeline Technical Specification (Technical Design Phase)
✓ Terraform Infrastructure Plan (Development Phase)
✓ Source-Target Lineage Diff & Reconciliation Report (Testing Phase)
✗ Updated Lakehouse Operational Runbook (Operations Phase)
```

---

# 34. FAILURE SCENARIO

Intentionally simulate one test failure to demonstrate continuous assurance and RCA.

Example:

```text
9 / 10 tests passed

FAILED

Lakehouse Source-Target Timestamp Reconciliation

Expected:
Timestamp Format = ISO-8601 (Microsecond Precision)
Reconciliation Drift < 0.1%

Actual:
Timestamp Format Mismatch (Legacy DW UTC String vs Parquet Epoch Microseconds)
Reconciliation Drift = 3.8% (3,820 customer records misaligned on date boundary)

Severity:
HIGH (Impacts Downstream Customer 360 Daily Partitioning)
```

Activate the Test Failure Analysis Agent automatically upon failure.

---

# 35. ROOT CAUSE ANALYSIS

Show the findings from the Test Failure Analysis Agent, tracing evidence back through Design and Implementation phases:

```text
Likely Root Cause

Source feed redirection to Lakehouse Parquet storage omitted explicit 
timestamp timezone normalization during the Data Design translation, 
causing legacy DW UTC text timestamps to be parsed as local epoch 
microseconds by the BigLake/Iceberg reader.

Evidence:
✓ Feasibility & Data Design Spec (lakehouse_customer_schema_mapping.v1.json)
✓ Git diff (pipelines/salesforce_customer_ingest.py)
✓ Data profile comparison (dw_staging.customer vs lakehouse_raw.customer)
✓ Technical Twin Lineage Graph
✓ Failed reconciliation test log
✓ Historical incident pattern (INC-2025-041)

Confidence:
93%
```

Never present unsupported reasoning as fact.

Use strict evidence confidence indicators:

```text
Observed
Inferred
Likely
Confirmed
```

---

# 36. DELIVERY GATE

Show the updated Delivery Gate status in the UI:

# Release Readiness Gate

```text
Feasibility & Design Sign-off  100% ✓
Regression & Parity Tests      9/10 ⚠
Data Quality Validation        14/14 ✓
Security & Governance           6/6 ✓
Evidence Completeness          85% ⚠
Checklist Compliance           92% ✓
Operational Readiness            0% ✕

Gate Status:
BLOCKED
```

Show:

```text
Reason:
Operational Runbook missing
Regression failure unresolved
```

Required approver:

```text
Solution Architect
```

---

# 37. HUMAN APPROVAL

Provide an approval panel:

```text
Release Readiness

[Approve]
[Approve With Conditions]
[Reject]
```

Approval must record:

```text
user
decision
timestamp
reason
evidence
```

For the prototype, use a simulated user.

---

# 38. REMEDIATION

The system recommends:

```text
1. Correct transformation
2. Add regression test
3. Add DQ rule
4. Update operational runbook
5. Re-run Release Readiness Gate
```

Allow:

```text
Create PR
```

to simulate creating a pull request.

Do not perform real destructive operations.

---

# 39. CONTINUOUS AGENT IMPROVEMENT

After the change scenario, demonstrate agent evolution.

Example:

```text
Documentation Agent

Current Trust:
79%

Reason:
12 new datasets not documented

Marketplace:
Candidate v2.3 found
```

Compare:

```text
                    Current    Candidate

Documentation       79%        94%
Coverage             82%        97%
Latency              8 sec      6 sec
Cost                 $0.18      $0.12
```

Run shadow evaluation.

Then:

```text
Candidate:
96%

Current:
91%

Policy:
PASS

Recommendation:
PROMOTE
```

Demonstrate:

```text
Current
   ↓
Candidate
   ↓
Shadow
   ↓
Evaluate
   ↓
Certified
   ↓
Promote
```

---

# 40. ORGANIZATIONAL LEARNING

The platform should maintain:

```text
Historical Decisions
Review Comments
Waivers
Defect Patterns
Gate Failures
Incident Lessons
Architecture Exceptions
Delivery Bottlenecks
```

These become Knowledge Packs.

Show an example:

```text
Pattern detected:

Streaming projects frequently fail
Operational Readiness.

Recommendation:

Automatically add Operational Readiness
Agent to future streaming projects.
```

---

# 41. UI REQUIREMENTS

The UI must be polished enough for an executive demonstration.

Use:

* responsive layout
* left navigation
* project switcher
* global search
* command palette
* breadcrumbs
* cards
* status badges
* progress indicators
* graphs
* charts
* tables
* drawers
* modal dialogs
* tabs
* tooltips
* evidence panels
* timeline/activity feed
* filters
* sorting
* search
* drill-down
* hover states
* empty states
* loading states
* error states

Use a consistent visual language.

Do not make it look like a developer-only admin console.

---

# 42. GLOBAL NAVIGATION

Use:

```text
Overview
Projects
Digital Twin
Delivery Model
Capabilities
Agents
Marketplace
Evaluations
Changes
Evidence
Activity
```

Within a project:

```text
Overview
Technical Twin
Delivery Twin
Capabilities
Agents
Tests
Changes
Gates
Evidence
Activity
```

---

# 43. UNIVERSAL "WHY?" FUNCTION

Every major recommendation must have:

```text
Why?
```

Examples:

```text
Why was this agent selected?
Why is this asset impacted?
Why was this test selected?
Why is this gate blocked?
Why is this agent trusted?
Why is this upgrade recommended?
```

The answer must display evidence references.

---

# 44. TRACEABILITY EXPLORER

Implement a visual traceability path:

```text
Requirement
   ↓
Delivery Task
   ↓
Agent
   ↓
Artifact
   ↓
Test
   ↓
Evidence
   ↓
Approval Gate
   ↓
Deployment
```

The user must be able to click through the chain.

This is a major demonstration feature.

---

# 45. AUDIT TRAIL

Record:

```text
Agent executions
Skill executions
Tool calls
Recommendations
Evidence
Evaluation results
Approvals
Changes
Deployments
Agent versions
Knowledge versions
Policy versions
```

Every significant event must have:

```text
timestamp
actor
component
action
result
evidence
```

---

# 46. SECURITY MODEL

For MVP implement conceptual RBAC:

```text
Viewer
Engineer
Architect
Approver
Administrator
```

Actions should respect:

```text
read
analyse
execute_test
recommend
create_pr
approve
deploy
```

No agent should have unrestricted privileges.

---

# 47. SAFETY MODEL

The prototype must demonstrate:

```text
Read-only analysis
        ↓
Recommendation
        ↓
Human approval
        ↓
Controlled write
```

Classify actions:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Require appropriate approval.

---

# 48. DATA MODEL IMPLEMENTATION

Use PostgreSQL for transactional data and Neo4j for graph relationships.

PostgreSQL should store:

```text
Projects
Agents
Skills
Tools
Delivery Models
Tasks
Checklists
Evaluations
Approvals
Policies
Versions
```

Neo4j should represent:

```text
Project relationships
Lineage
Dependencies
Capability graph
Agent dependency graph
Delivery traceability
Impact analysis
```

Provide seed scripts.

---

# 49. MOCK DATA

Create a complete demo dataset.

Include:

```text
Customer 360 project

Pipelines:
40+

Data assets:
100+

Tests:
30+

Delivery phases:
8+

Tasks:
30+

Checklists:
10+

Approval gates:
6+

Agents:
15+

Skills:
30+

Tools:
10+

Knowledge packs:
8+

Policies:
6+

Evaluation suites:
10+
```

The numbers do not need to be exact, but the graph must be internally consistent.

---

# 50. DEMO SCENARIOS

Implement three pre-built scenarios.

## Scenario 1 — Assimilation

```text
Onboard Customer 360
→ Discover
→ Build Digital Twin
→ Discover Delivery Model
→ Identify gaps
```

## Scenario 2 — Change Assurance

```text
Simulate Source Feed Redirection to Lakehouse
→ Feasibility Assessment & Risk Analysis
→ Data & Technical Design
→ Pipeline Implementation
→ Technical & Delivery impact
→ Reconciliation & Test selection
→ Failure & Root cause
→ Governance Gate
```

## Scenario 3 — Agent Evolution

```text
Agent performance declines
→ Marketplace candidate
→ Evaluation
→ Shadow deployment
→ Promotion
```

A user should be able to reset the scenario and replay it.

---

# 51. DEMO MODE

Add a:

# Demo Mode

button.

Demo Mode should:

* seed/reset the project
* execute scripted agent events
* animate workflows
* simulate tool calls
* simulate test execution
* generate realistic evidence
* produce deterministic results
* allow the presenter to pause/resume

The presenter should be able to complete the entire demonstration in approximately 5–10 minutes.

---

# 52. PRODUCT STORY IN THE UI

The UI should progressively communicate:

### Stage 1

> We understand your existing system.

### Stage 2

> We understand how your organization delivers it.

### Stage 3

> We identify where your engineering process has gaps.

### Stage 4

> We compose the right engineering workforce.

### Stage 5

> We prove that workforce is trustworthy.

### Stage 6

> We continuously operate alongside your team.

### Stage 7

> We learn and improve.

---

# 53. MVP ACCEPTANCE CRITERIA

The MVP is successful only if a presenter can demonstrate:

### Assimilation

* Connect an existing project.
* Discover technical artifacts.
* Discover delivery documentation.
* Build the Digital Twin.
* Show technical and delivery relationships.

### Understanding

* Show project architecture.
* Show delivery phases.
* Show tasks.
* Show checklists.
* Show gates.
* Show capability health.
* Show gaps.

### Composition

* Recommend engineering roles.
* Select agents.
* Select skills.
* Select tools.
* Bind knowledge and policies.
* Explain why components were selected.

### Evaluation

* Run evaluation scenarios.
* Display scores.
* Display evidence.
* Certify agents.

### Deployment

* Deploy ecosystem.
* Show autonomy levels.
* Show permissions.
* Show active agents.

### Brownfield operation

* Detect a simulated change.
* Calculate technical impact.
* Calculate delivery impact.
* Select tests.
* Execute tests.
* Produce evidence.
* Detect failure.
* Perform root-cause analysis.
* Evaluate delivery gate.
* Block or approve change.

### Evolution

* Detect an underperforming agent.
* Find marketplace candidate.
* Evaluate candidate.
* Shadow candidate.
* Promote candidate.

If these work, the MVP demonstrates the complete concept.

---

# 54. IMPORTANT PROTOTYPE PRINCIPLE

Do not spend most of the effort implementing real cloud integrations.

The MVP's intellectual proof is:

```text
METAMODEL
    +
DIGITAL TWIN
    +
DELIVERY MODEL
    +
CAPABILITY GRAPH
    +
AGENT MARKETPLACE
    +
EVALUATION HARNESS
    +
BROWNFIELD CHANGE LOOP
```

Real infrastructure adapters can come later.

Use simulated adapters where necessary, but make their interfaces realistic.

---

# 55. ARCHITECTURAL EXTENSIBILITY

The prototype must make these replaceable:

```text
LLM provider
Agent runtime
Graph database
Cloud platform
Tool adapters
Evaluation engine
Vector store
UI
```

Do not put vendor-specific logic into the domain model.

Represent:

```text
Capability
    ↓
Platform Binding
    ↓
Technology
    ↓
Tool
```

Example:

```text
Streaming
    ↓
GCP
    ↓
Pub/Sub + Dataflow
```

and:

```text
Streaming
    ↓
AWS
    ↓
Kinesis
```

The same agent should conceptually operate at the capability level.

---

# 56. TESTING

Provide:

### Unit tests

For:

```text
metamodel
dependency resolution
impact analysis
capability mapping
delivery gate evaluation
agent selection
policy enforcement
```

### Integration tests

For:

```text
PostgreSQL
Neo4j
API
worker
marketplace
evaluation harness
```

### End-to-end test

Test:

```text
Assimilate
→ Compose
→ Evaluate
→ Deploy
→ Simulate Change
→ Impact
→ Test
→ Gate
→ Evidence
```

---

# 57. DOCUMENTATION

Produce:

```text
README.md
ARCHITECTURE.md
METAMODEL.md
DELIVERY_TYPES.md
DELIVERY_BLUEPRINTS.md
DELIVERY_MODEL.md
AGENT_MODEL.md
MARKETPLACE.md
EVALUATION.md
SECURITY.md
DEMO_GUIDE.md
API.md
ADR/
```

Include diagrams.

---

# 58. BUILD ORDER

Do not attempt to implement everything simultaneously.

Build vertical slices.

## Slice 1

```text
Metamodel
+
Seed project
+
Project graph
+
Basic UI
```

## Slice 2

```text
Technical assimilation
+
Delivery document assimilation
+
Digital Twin
```

## Slice 3

```text
Capability analysis
+
Marketplace
+
Agent composition
```

## Slice 4

```text
Evaluation
+
Certification
+
Deployment
```

## Slice 5

```text
Change detection
+
Technical impact
+
Delivery impact
```

## Slice 6

```text
Test execution
+
Evidence
+
Approval Gate
```

## Slice 7

```text
Agent evolution
+
Shadow evaluation
+
Promotion
```

After each slice:

* run automated tests
* verify UI
* update documentation
* preserve architectural boundaries

---

# 59. WHAT NOT TO DO

Do NOT:

* build a generic chatbot
* create dozens of fully autonomous agents
* make LLM calls mandatory for every operation
* hard-code GCP into the metamodel
* treat documentation as unstructured prompt context
* treat agents as the primary abstraction
* allow unrestricted writes
* fabricate evaluation scores without underlying scenarios
* expose chain-of-thought
* create a marketplace with no dependency model
* build elaborate enterprise IAM for the prototype
* build payment/subscription functionality
* build multi-cloud execution in the first MVP

---

# 60. SUCCESS CRITERION

The final prototype should allow an executive to understand the concept without reading the architecture documentation.

Within 5–10 minutes the presenter should be able to show:

```text
"We inherited this project."

        ↓

"We understand its technical architecture."

        ↓

"We understand what you are delivering and instantiate
the organization's delivery blueprint."

        ↓

"We found capability and process gaps."

        ↓

"We composed an engineering-agent workforce aligned to
the delivery blueprint."

        ↓

"We evaluated and certified that workforce."

        ↓

"We deployed it into the project."

        ↓

"Now a developer makes a change."

        ↓

"The system classifies the change, calculates both
technical and delivery impact."

        ↓

"It automatically selects and executes the
appropriate validation."

        ↓

"It collects evidence."

        ↓

"It evaluates the approval gate."

        ↓

"It blocks unsafe delivery."

        ↓

"It learns from the outcome."

        ↓

"It can even evaluate and upgrade its
own engineering agents."
```

The final screen should communicate:

# From AI Assistants

# → to a Living Engineering Organization

The system should feel like a **digital engineering organization attached to an existing data platform**, not an AI chatbot sitting beside it.

The durable architecture is:

```text
Technical Digital Twin
          +
Delivery Digital Twin
          ↓
  Delivery Type & Blueprint
          ↓
     Project Graph
          ↓
 Capability & Gap Graph
          ↓
 Context-Aware Agent Composition
          ↓
 Evaluation & Certification
          ↓
 Controlled Deployment
          ↓
 Technical + Delivery Impact
          ↓
 Continuous Engineering
          ↓
 Learning & Evolution
```

Build the prototype around this loop.

---

# ADDENDUM — CAPABILITY GRAPH & ONBOARDING

## 1. Agent & Skill Marketplace Catalogue

The Agentic Data Engineering framework operates on a **dependency-aware capability graph**. It is not a flat list of AI bots.

The marketplace is structured as follows:

```text
Problem ➔ Capability ➔ Engineering Role ➔ Agent ➔ Skill ➔ Tool ➔ Knowledge ➔ Policy ➔ Evaluation ➔ Certification
```

### Marketplace Component Types
- **ENGINEERING_ROLE**: Stable engineering responsibilities (e.g., Regression Engineer, Data Architect).
- **AGENT**: Specific implementations of roles (e.g., `regression-test-agent`, `project-discovery-agent`).
- **SKILL**: Reusable execution units (e.g., `schema-discovery`, `impact-analysis`).
- **TOOL**: Infrastructure adapters (e.g., BigQuery, GitHub, dbt).
- **KNOWLEDGE_PACK**: Contextual grounding (e.g., architecture standards, naming conventions).
- **POLICY**: Constraints on behavior (e.g., production write approvals).
- **EVALUATION_SUITE**: Verification tests that agents must pass.
- **CERTIFICATION**: Proof of deployability.

### Composition Engine
The marketplace graph allows the system to answer queries like: "Given this data engineering problem and this existing technology landscape, which engineering roles, agents, skills, tools, knowledge and evaluation suites should be composed?"

---

## 2. Business Application Onboarding Flow

Before a change request is processed, a business application (or project) must be onboarded into the ecosystem. This establishes a baseline in the Knowledge Graph.

The **Project Discovery Wizard** flow consists of four phases:

### Phase 1: Repository & Discovery
- **Agent**: `project-discovery-agent`
- **Action**: The user provides a repository URL (e.g., GitHub). The agent scans the source tree, classifies files, extracts dependencies, detects the technology stack (e.g., dbt, Airflow), and identifies implicit coding standards and Data Quality (DQ) test suites.

### Phase 2: Architecture Discovery
- **Agent**: `architecture-discovery-agent`
- **Action**: Infers the technical architecture of the application. It maps source systems, storage layers (Lakehouse/Warehouse), and transformation models (dbt) directly into the central Knowledge Graph as a foundational Technical Twin.

### Phase 3: Historical Analysis
- **Agent**: `metadata-discovery-agent`
- **Action**: Analyzes historical metadata (JIRA tickets, ServiceNow CRs, pull requests). It determines the prevalence of standard artifacts historically and detects instances of architectural drift over time.

### Phase 4: Playbook & Gap Analysis
- **Agent**: `solution-architecture-agent`
- **Action**: Generates a tailored **Delivery Playbook**. It models the gaps between the application's current state and expected enterprise standards. If gaps are found (e.g., missing data contract testing), the playbook automatically augments future Delivery Blueprints for this specific application to include specialized agents (e.g., `data-contract-agent`) during the execution of standard SDLC phases.
