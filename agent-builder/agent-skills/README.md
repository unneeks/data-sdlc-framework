# Agent Skills Catalogue

Skills are reusable capability modules that agents can activate. Each skill
has an ID, description, layer, and applicability condition.

## Layers

| Layer | Name | Description |
|---|---|---|
| 1 | Foundation | Always active, not role-specific |
| 2 | Core | Always active for this agent role |
| 3 | Conditional | Activated based on context fields |

## Registered Skills

| Skill ID | Description | Layer |
|---|---|---|
| `delivery_model_analysis` | Read and classify delivery model activities | 2 |
| `activity_classification` | Classify activities by agent involvement (OWNS/CONTRIBUTES/CONSUMES) | 2 |
| `entity_extraction` | Extract design fields (tasks, inputs, outputs) from activity documents | 2 |
| `agent_splitting_evaluation` | Evaluate whether to split agent into sub-agents (7 criteria) | 2 |
| `skill_mapping` | Map responsibilities to skills, check for duplicates | 2 |
| `design_document_rendering` | Render 13-section agent design document | 2 |
| `manifest_generation` | Generate agent-template.yaml from design | 2 |
| `graphify_analysis` | Code analysis and architecture extraction for engineer roles | 3 |
| `confluence_fetch` | Fetch delivery model pages from wiki | 3 |
