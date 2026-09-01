---
name: sdlc-orchestrator
description: State machine for SDLC document approval and agent orchestration workflow
version: "1.0"
---

# SDLC Orchestrator State Machine

## States

### INIT
- description: Workflow not yet started
- transitions:
  - event: start_workflow
    target: REQUIREMENTS_REVIEW
    action: initialize_documents

### REQUIREMENTS_REVIEW
- description: Requirements document awaiting review and approval
- documents:
  - id: requirements-doc
    title: Requirements Specification
    status: DRAFT
- transitions:
  - event: approve_document
    condition: document_id == "requirements-doc"
    target: DESIGN_REVIEW
    action: finalize_document

### DESIGN_REVIEW
- description: Design document awaiting review and approval
- documents:
  - id: design-doc
    title: System Design Document
    status: DRAFT
- transitions:
  - event: approve_document
    condition: document_id == "design-doc"
    target: TEST_PLANNING
    action: invoke_agent
    agent: test-planner-agent
    task: Generate test plan based on approved requirements and design documents

### TEST_PLANNING
- description: Test plan agent is generating a test plan draft
- agent: test-planner-agent
- transitions:
  - event: agent_completed
    target: TEST_PLAN_REVIEW
    action: present_draft
    artifact: test-plan-draft

### TEST_PLAN_REVIEW
- description: Test plan draft awaiting review and approval
- documents:
  - id: test-plan
    title: Test Plan
    status: DRAFT
- transitions:
  - event: approve_document
    condition: document_id == "test-plan"
    target: COMPLETED
    action: finalize_document

### COMPLETED
- description: All documents approved, workflow complete
- terminal: true

## Agent Mapping

| State              | Event             | Agent                  | Purpose                                    |
|--------------------|-------------------|------------------------|--------------------------------------------|
| DESIGN_REVIEW      | approve_document  | test-planner-agent     | Generate test plan from approved artifacts |

## Document Lifecycle

DRAFT -> APPROVED -> FINALIZED

Documents start as DRAFT when their state is entered.
On approve_document event, status moves to APPROVED.
On finalize_document action, status moves to FINALIZED.
