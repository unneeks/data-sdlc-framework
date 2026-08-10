# Agentic Data Engineering Framework - Features & Updates Changelog

This document tracks significant feature additions and specification updates to the Agentic Data Engineering Framework.

## Update: Business Application Onboarding Flow & Marketplace Integration (Aug 2026)

### 1. Business Application Onboarding Wizard
Added a new interactive onboarding flow designed for discovering and onboarding entire business applications (projects) into the ecosystem *before* any change requests are made.

**Features:**
- **Repository & Tech Scan:** Uses `project-discovery-agent` to scan GitHub repositories, infer tech stacks (e.g., dbt, Airflow, Terraform), and detect existing test suites (Data Quality).
- **Architecture Discovery:** Uses `architecture-discovery-agent` to reverse-engineer technical layers (Source, Storage, Transform) and maps them into a central Knowledge Graph.
- **Historical Analysis:** Uses `metadata-discovery-agent` to analyze historical PRs, JIRA tickets, and Change Requests to detect standard artifact prevalence and architectural drift.
- **Playbook Generation:** Uses `solution-architecture-agent` to establish a baseline "Delivery Playbook," showing the current conformance to expected standards and highlighting gaps to automatically augment future Delivery Blueprints.

### 2. Premium User Interface Overhaul
- **Dark Mode Aesthetic:** Fully styled using Tailwind CSS with glassmorphism panels, deep slate backgrounds, and glowing accents.
- **Framer Motion Integration:** Staggered list reveals, smooth tab transitions, and animated timeline nodes.
- **Component Redesigns:**
  - `Sidebar`: Vertical tab navigation.
  - `HeroDemoSimulation`: Connected vertical timeline showing multi-agent SDLC progression and live terminal logs.
  - `DigitalTwinExplorer`: Dual-view graphical lineage layout bridging Technical and Delivery twins.
  - `DeliveryTypeOnboarding`: AI chat-like classification gateway.
  - `MarketplaceComposer`: Grid showing agent roles, trust scores, and capabilities.
  - `CliIntegrationExplorer`: Interactive sandbox for `gemini-agent run` and `gh copilot agent run`.
  - `ImpactAndRCAViewer`: Graphical representation of test failures and Root Cause Analysis logic.
  - `DeliveryGateApproval`: Checklists enforcing verifiable evidence checks before PR creation.

### 3. Agent & Skill Marketplace Catalogue
The system architecture has been updated to incorporate a machine-readable dependency-aware capability graph. 
- **Roles:** Defined stable engineering responsibilities (e.g., Regression Engineer, Data Architect).
- **Agents:** Implementations of roles (e.g., `regression-test-agent`, `project-discovery-agent`).
- **Skills:** Reusable execution units (e.g., `schema-discovery`, `impact-analysis`).
- **Knowledge & Policies:** Governs constraints and contextual grounding.
- **Evaluation & Certification:** Agents must be certified against evaluation suites before they are marked as deployable.
