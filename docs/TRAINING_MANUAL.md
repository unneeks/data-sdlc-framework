# Data SDLC Framework — Training Manual

**A Friendly Guide for Everyone**

**Version:** 1.0
**Last Updated:** 2026-08-30

---

## Who Is This Manual For?

This manual is for anyone who wants to understand and use the Data SDLC Framework —
whether you are a developer, a project manager, a team lead, or someone who is simply
curious about how AI agents can help automate parts of software delivery.

No prior experience with AI agents, knowledge graphs, or AWS is assumed. We will explain
everything from the ground up, using everyday analogies and step-by-step instructions.

---

## Table of Contents

- [Part 1: Getting Started](#part-1-getting-started)
  - [What Is This Project?](#what-is-this-project)
  - [What You Need](#what-you-need)
  - [Project Structure](#project-structure)
  - [Quick Start — Your First Discovery](#quick-start--your-first-discovery)
- [Part 2: The Discovery Agent](#part-2-the-discovery-agent)
  - [What Does It Do?](#what-does-the-discovery-agent-do)
  - [The 4-Pass Process](#the-4-pass-process)
  - [Running Discovery Locally](#running-discovery-locally)
  - [Running via AgentCore Harness](#running-discovery-via-agentcore-harness)
  - [Running via Claude Code](#running-discovery-via-claude-code)
  - [Understanding the Results](#understanding-discovery-results)
  - [The 4 Discovery Modes](#the-4-discovery-modes)
- [Part 3: The Agent Builder](#part-3-the-agent-builder)
  - [What Does It Do?](#what-does-the-agent-builder-do)
  - [The 8-Step Process](#the-8-step-process)
  - [The 7 Splitting Criteria](#the-7-splitting-criteria)
  - [Running via Claude Code](#running-the-agent-builder-via-claude-code)
  - [Running via AgentCore Harness](#running-the-agent-builder-via-agentcore-harness)
  - [Running via GitHub Copilot CLI](#running-the-agent-builder-via-github-copilot-cli)
  - [Understanding the Outputs](#understanding-the-agent-builder-outputs)
- [Part 4: Working with AgentCore Harness](#part-4-working-with-agentcore-harness)
  - [What Is a Harness?](#what-is-a-harness)
  - [Creating Your Harness](#creating-your-harness)
  - [Invoking a Harness](#invoking-a-harness)
  - [Inline Function Tools](#inline-function-tools)
  - [Control Plane vs Data Plane](#control-plane-vs-data-plane)
- [Part 5: Testing](#part-5-testing)
  - [Running the Test Suite](#running-the-test-suite)
  - [What the Tests Cover](#what-the-tests-cover)
  - [Using the Test-Data Folder](#using-the-test-data-folder)
- [Part 6: Common Tasks (Cookbook)](#part-6-common-tasks-cookbook)
  - [Scan My Repository](#i-want-to-scan-my-repository)
  - [Design a New Agent](#i-want-to-design-a-new-agent)
  - [Add a New Discovery Strategy](#i-want-to-add-a-new-discovery-strategy)
  - [Update the Harness](#i-want-to-update-the-harness)
- [Part 7: Troubleshooting](#part-7-troubleshooting)
- [Part 8: Glossary](#part-8-glossary)

---

# Part 1: Getting Started

## What Is This Project?

Imagine you have a large codebase — hundreds of files, data pipelines, SQL scripts,
infrastructure configurations, project documents. Understanding what everything does
and how it connects is like walking into a large library with no catalog.

**This project gives you two AI-powered assistants:**

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                   Data SDLC Framework                            │
  │                                                                  │
  │  ┌─────────────────────┐     ┌──────────────────────────────┐   │
  │  │   Discovery Agent   │     │      Agent Builder           │   │
  │  │                     │     │                              │   │
  │  │  "The Librarian"    │     │  "The Architect"             │   │
  │  │                     │     │                              │   │
  │  │  Scans your code    │     │  Reads your team's process   │   │
  │  │  and builds a map   │     │  docs and designs AI agents  │   │
  │  │  of everything      │     │  that can help your team     │   │
  │  └─────────────────────┘     └──────────────────────────────┘   │
  └──────────────────────────────────────────────────────────────────┘
```

**Think of it like this:**

- **Discovery Agent** = A librarian who walks through your entire library, reads every
  book, and creates a catalog card for each one — noting what it is, where it lives,
  and how it connects to other books.

- **Agent Builder** = An architect who reads your team's "how we work" handbook and
  designs specialized AI assistants for specific roles (like a Data Engineer bot or a
  Release Manager bot).


## What You Need

Before you start, make sure you have these tools installed:

| Tool | What It Is | How to Check |
|------|-----------|--------------|
| **Python 3.11+** | The programming language everything runs on | `python3 --version` |
| **uv** | A fast Python package manager (like pip, but faster) | `uv --version` |
| **AWS CLI** | Command-line tool for Amazon Web Services | `aws --version` |
| **AWS Credentials** | Your "key card" to access AWS services | `aws sts get-caller-identity` |
| **Git** | Version control (you probably already have this) | `git --version` |

### Installing uv (if you don't have it)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Checking AWS Credentials

```bash
# This should show your account ID and username — not an error
aws sts get-caller-identity
```

If you see an error, you need to configure your AWS credentials first:

```bash
aws configure
# Enter your Access Key ID, Secret Key, region (us-west-2), and output format (json)
```


## Project Structure

Here is how the project is organized. Think of it like floors in a building:

```
data-sdlc-framework/
│
├── discovery/                          # Floor 1: The Discovery Agent
│   ├── tools/                          #   Its toolbox
│   │   ├── walk.py                     #     Tool: walk through files
│   │   ├── read.py                     #     Tool: read file contents
│   │   └── ingest.py                   #     Tool: save findings to the map
│   ├── skills/                         #   Instruction manuals for different modes
│   │   ├── repository-discovery.md     #     Full scan instructions
│   │   ├── repository-discovery-quick.md   # Quick scan instructions
│   │   ├── repository-discovery-dbt.md     # dbt specialist instructions
│   │   └── repository-discovery-delta.md   # Changes-only instructions
│   ├── registry.py                     #   Strategy selector
│   ├── invoke_harness.py               #   Cloud runner (AWS)
│   └── strategy.py                     #   Base pattern for all strategies
│
├── agent-builder/                      # Floor 2: The Agent Builder
│   ├── core/                           #   Shared logic (works everywhere)
│   │   ├── models.py                   #     Data structures
│   │   ├── analyser.py                 #     Reads delivery model files
│   │   ├── splitter.py                 #     Should we split this agent?
│   │   ├── skills.py                   #     Skill catalogue manager
│   │   └── renderer.py                 #     Generates output documents
│   ├── platforms/                      #   Platform-specific adapters
│   │   ├── claude-code/                #     For Claude Code (terminal)
│   │   ├── agentcore-harness/          #     For AWS cloud
│   │   └── github-copilot/             #     For GitHub Copilot CLI
│   └── agent-skills/                   #   Catalogue of reusable skills
│       └── README.md
│
├── agents/                             # Floor 3: Harness Deployment Scripts
│   └── harness_agents/
│       ├── create_discovery_agent.py   #   Deploy discovery agent to AWS
│       ├── create_agent_builder.py     #   Deploy agent builder to AWS
│       └── create_all.py              #   Deploy both at once
│
├── tests/                              # Floor 4: Quality Assurance
│   ├── test_discovery.py               #   71 tests for discovery
│   └── test_agent_builder.py           #   74 tests for agent builder
│
├── test-data/                          # Floor 5: Sample Repository
│   ├── code/                           #   Sample SQL, Python, dbt files
│   ├── docs/                           #   Sample documentation
│   ├── infrastructure/                 #   Sample Terraform, Docker files
│   └── ci-cd/                          #   Sample CI/CD workflows
│
└── prompts/                            # Floor 6: AI Instructions
    └── agent-builder.prompt.md         #   Full instructions for agent builder
```


## Quick Start — Your First Discovery

Let's run the Discovery Agent against the included sample repository. This takes
about 30 seconds and requires no AWS credentials.

```bash
# Step 1: Go to the project directory
cd data-sdlc-framework

# Step 2: Run the tests to verify everything works
uv run --with pytest pytest tests/test_discovery.py -v --tb=short

# Step 3: Run a quick discovery in Python
uv run python -c "
from discovery.tools.walk import walk_repository
from discovery.tools.ingest import ingest_entities, get_graph_state

# Walk the test-data repository
result = walk_repository('test-data')
print(f'Found {result[\"total_candidates\"]} candidate files')
print(f'Technical: {len(result[\"technical\"])} files')
print(f'Delivery:  {len(result[\"delivery\"])} files')
print()
print('Files by type:')
for kind, count in result['by_source_kind'].items():
    print(f'  {kind}: {count}')
"
```

You should see output like:

```
Found 45 candidate files
Technical: 30 files
Delivery:  15 files

Files by type:
  sql: 12
  python: 5
  terraform: 4
  dockerfile: 2
  compose: 1
  ci_workflow: 4
  markdown: 15
  yaml_config: 2
```

Congratulations — you just ran your first discovery!

---

# Part 2: The Discovery Agent

## What Does the Discovery Agent Do?

Think of the Discovery Agent as a **detective** who investigates your codebase. It:

1. **Walks** through every folder and file
2. **Reads** and understands what each file contains
3. **Identifies** important things (pipelines, data tables, infrastructure, etc.)
4. **Maps** how everything connects to everything else
5. **Builds** a knowledge graph — a structured map of your entire project

```
   Your Codebase                    Knowledge Graph
   ┌─────────────┐                 ┌───────────────────────────┐
   │ models/      │                │                           │
   │  staging/    │    Discovery   │  [Pipeline]               │
   │   stg_*.sql  │ ──────────▶   │    │                      │
   │  marts/      │    Agent       │    ├── PRODUCES ──▶ [DataAsset]
   │   dim_*.sql  │                │    │                  │   │
   │ Dockerfile   │                │    └── DEPENDS_ON     │   │
   │ terraform/   │                │       [Infrastructure] │  │
   │ docs/*.md    │                │           HAS_SCHEMA ──┘  │
   └─────────────┘                 └───────────────────────────┘
```


## The 4-Pass Process

The Discovery Agent works in four passes, like a thorough inspector:

### Pass 1: Walk and Classify ("What's in the building?")

The agent walks through every folder, looks at file names and extensions,
and sorts them into categories:

| File Type | Category | What It Might Contain |
|-----------|----------|----------------------|
| `.sql` | Technical | Data pipelines, table definitions |
| `.py` (with "dag" or "pipeline") | Technical | Airflow DAGs, ETL scripts |
| `.tf` | Technical | Infrastructure (Terraform) |
| `Dockerfile` | Technical | Container definitions |
| `.github/workflows/*.yml` | Technical | CI/CD pipelines |
| `.md` | Delivery | Documentation, requirements, plans |

**Think of it like:** A postal worker sorting mail into "bills", "letters", and
"packages" just by looking at the envelope — they don't open anything yet.

### Pass 2: Technical Extraction ("What's inside each technical file?")

Now the agent reads each technical file and identifies entities:

- **Pipeline** — An automated workflow (like an Airflow DAG or dbt model)
- **DataAsset** — A table, view, dataset, or file
- **Infrastructure** — A server, container, or cloud resource
- **CodeArtifact** — A reusable piece of code (function, class, module)
- **SchemaDefinition** — A description of data structure (column types, etc.)

**Think of it like:** Opening each letter and noting "this is an invoice from
Company X for $500, related to Project Y."

### Pass 3: Delivery Extraction ("What's in the project docs?")

The agent reads each Markdown/doc file and identifies delivery entities:

- **Task** — A work item or action item
- **Checklist** — An ordered list of things to verify
- **Gate** — A quality checkpoint ("must pass before proceeding")
- **DeliveryArtifact** — A document, report, or sign-off
- **EvidenceRequirement** — Proof needed to pass a gate

**Think of it like:** Reading through a project's filing cabinet and noting
every to-do list, approval form, and compliance checklist.

### Pass 4: Resolve and Finalize ("How does everything connect?")

The agent finds relationships between everything it discovered:

| Relationship | What It Means | Example |
|-------------|--------------|---------|
| DEPENDS_ON | A needs B to work | Pipeline depends on a data source |
| PRODUCES | A creates B | Pipeline produces a table |
| HAS_SCHEMA | A is structured like B | Table has a schema definition |
| CONTAINS | A holds B inside it | Folder contains files |
| DESCRIBES | A documents B | README describes a pipeline |
| GOVERNS | A controls B | Quality gate governs deployment |
| VALIDATED_BY | A is checked by B | Pipeline is validated by tests |

**Think of it like:** Drawing lines on a corkboard between related index cards,
creating a visual map of "this leads to that."


## Running Discovery Locally

The simplest way — no cloud services needed. Runs entirely on your computer.

```bash
cd data-sdlc-framework

# Run full batch discovery against the test-data repository
uv run python -c "
from discovery.tools.walk import walk_repository
from discovery.tools.read import read_file
from discovery.tools.ingest import ingest_entities, ingest_relationships, get_graph_state

# Pass 1: Walk
walk_result = walk_repository('test-data')
print(f'Pass 1: Found {walk_result[\"total_candidates\"]} files')

# Pass 2 & 3: Read each file and extract entities
all_entities = []
for f in walk_result['technical'] + walk_result['delivery']:
    content = read_file('test-data', f['path'])
    # In batch mode, you would use an LLM to extract entities from content
    # For now, we create basic entities from file metadata:
    all_entities.append({
        'entity_type': f['entity_types'][0] if f['entity_types'] else 'CodeArtifact',
        'name': f['path'].split('/')[-1].replace('.', '_'),
        'source_document': f['path'],
        'provenance': 'OBSERVED',
        'confidence': 1.0,
    })

# Ingest
result = ingest_entities('my-project', all_entities)
print(f'Pass 2-3: Ingested {result[\"ingested\"]} entities')

# Check the graph
state = get_graph_state('my-project')
print(f'Graph: {state[\"entity_count\"]} entities, {state[\"relationship_count\"]} relationships')
print()
print('Entities by type:')
for e in state['entities'][:5]:
    print(f'  [{e[\"entity_type\"]}] {e[\"name\"]}')
print(f'  ... and {len(state[\"entities\"]) - 5} more')
"
```


## Running Discovery via AgentCore Harness

This runs the Discovery Agent in the AWS cloud. The AI (Claude Opus 4.6) reads your
files, decides what to extract, and calls tools on your machine to save results.

**Prerequisites:** AWS credentials configured, harness already created.

```bash
# Run the harness-based discovery
uv run python -m discovery.invoke_harness test-data my-project-id
```

What happens behind the scenes:

```
  Your Computer                         AWS Cloud (AgentCore)
  ┌─────────────────┐                  ┌─────────────────────┐
  │                  │   1. Start       │                     │
  │  invoke_harness  │ ──────────────▶  │  Claude Opus 4.6    │
  │                  │                  │  (The AI Brain)     │
  │                  │   2. "Call       │                     │
  │                  │ ◀── walk_repo"   │  Decides what to do │
  │                  │                  │  next based on      │
  │  walk_repository │   3. Results     │  what it sees       │
  │  (runs locally)  │ ──────────────▶  │                     │
  │                  │                  │                     │
  │                  │   4. "Call       │                     │
  │                  │ ◀── read_file"   │                     │
  │                  │                  │                     │
  │  read_file       │   5. Results     │                     │
  │  (runs locally)  │ ──────────────▶  │                     │
  │                  │                  │                     │
  │  ... repeats     │   ...            │  ... thinks, reads, │
  │  until done ...  │                  │  extracts ...       │
  │                  │                  │                     │
  │                  │   N. "Done"      │                     │
  │  Final graph     │ ◀────────────── │  "I found 256       │
  │  saved locally   │                  │   entities"         │
  └─────────────────┘                  └─────────────────────┘
```


## Running Discovery via Claude Code

If you are using Claude Code (the CLI tool or IDE extension), the Discovery Agent
works interactively — you can watch it think and ask it questions.

In your Claude Code session:

```
You: Discover the repository at ./test-data and build a knowledge graph

Claude: I'll walk the repository, extract entities, and build the graph.
        Let me start with a directory walk...

        [Calls walk_repository]
        Found 45 candidate files (30 technical, 15 delivery)

        Now reading technical files...
        [Reads SQL files, identifies pipelines and tables]
        [Reads Terraform files, identifies infrastructure]

        Found 97 entities and 45 relationships.
```


## Understanding Discovery Results

After discovery runs, you get a **knowledge graph** — a structured map of your project.

### What Does an Entity Look Like?

```json
{
  "entity_id": "pipeline:atlas_daily_dbt",
  "entity_type": "Pipeline",
  "name": "atlas_daily_dbt",
  "project_id": "my-project",
  "provenance": "OBSERVED",
  "confidence": 1.0,
  "source_document": "code/dbt/models/staging/stg_orders.sql",
  "attributes": {
    "technology": "dbt",
    "schedule": "daily"
  }
}
```

Each entity has:

| Field | What It Means |
|-------|--------------|
| `entity_id` | A unique ID like `pipeline:atlas_daily_dbt` |
| `entity_type` | The category (Pipeline, DataAsset, etc.) |
| `name` | A human-readable name |
| `provenance` | How we found it: OBSERVED (seen directly) or INFERRED (guessed) |
| `confidence` | How sure we are: 1.0 = certain, 0.5 = uncertain |
| `source_document` | Which file it came from |

### What Does a Relationship Look Like?

```json
{
  "relationship_type": "PRODUCES",
  "source_ref": "pipeline:atlas_daily_dbt",
  "target_ref": "dataasset:dim_customers",
  "confidence": 0.9
}
```

This says: "The `atlas_daily_dbt` pipeline **produces** the `dim_customers` table."

### Confidence Scoring

| Score | Meaning | Example |
|-------|---------|---------|
| 1.0 | Explicitly stated in the code | `CREATE TABLE customers` |
| 0.9 | Strongly implied | A dbt model that references a source |
| 0.7 | Inferred from patterns | A file named `etl_pipeline.py` |
| 0.5 | Uncertain, needs verification | A comment mentioning "dashboard" |


## The 4 Discovery Modes

Different situations call for different levels of thoroughness:

### 1. Full Discovery (The Deep Dive)

**Skill file:** `repository-discovery.md`
**When to use:** First-time scan of a new repository
**What it does:** Reads every file, extracts every entity, maps all relationships
**Speed:** Slow (reads everything)

```
Think of it like: A home inspector who checks every room, every wall,
every pipe, and every wire. Thorough but takes time.
```

### 2. Quick Discovery (The Flyover)

**Skill file:** `repository-discovery-quick.md`
**When to use:** Quick inventory, time-limited scans
**What it does:** Top-level entities only, max 50 files, confidence >= 0.9 only
**Speed:** Fast (skips uncertain findings)

```
Think of it like: A real estate agent doing a quick walkthrough —
notes the big things (3 bedrooms, 2 baths) but doesn't check the plumbing.
```

### 3. dbt Specialist (The Expert)

**Skill file:** `repository-discovery-dbt.md`
**When to use:** Repositories that use dbt (data build tool)
**What it does:** Understands dbt-specific patterns: models, sources, seeds, tests
**Speed:** Medium (focused on dbt files)

```
Think of it like: Calling in a plumbing specialist instead of a general
inspector — they know exactly what to look for in their domain.
```

Mapping:

| dbt Concept | Entity Type |
|------------|-------------|
| Model (`.sql` in models/) | Pipeline |
| Source (in `sources.yml`) | DataAsset |
| Seed (`.csv` in seeds/) | DataAsset |
| Test (in `schema.yml`) | EvidenceRequirement |

### 4. Delta Discovery (The Updater)

**Skill file:** `repository-discovery-delta.md`
**When to use:** After code changes (only scan what changed)
**What it does:** Uses `git diff` to find changed files, only scans those
**Speed:** Very fast (only processes changes)

```
Think of it like: A security guard checking only the rooms where
the alarm went off, not the entire building.
```

Status tags for delta mode:

| Status | Meaning |
|--------|---------|
| ADDED | New entity discovered in changed files |
| MODIFIED | Existing entity updated |
| UNCHANGED | Entity existed before, still valid |
| DELETED | Entity was in a deleted file |

---

# Part 3: The Agent Builder

## What Does the Agent Builder Do?

The Agent Builder reads your team's **delivery model** — the documents that describe
how your team works (phases, activities, roles, responsibilities) — and designs an
AI agent for a specific role.

**Example:** Your team has a delivery model with 30 activities across 6 phases. You
ask: "Design a Data Engineer agent." The Agent Builder reads all 30 activities,
figures out which ones the Data Engineer owns, contributes to, or consumes from, and
produces a complete design document.

```
  Delivery Model                  Agent Builder              Agent Design
  ┌──────────────┐               ┌──────────────┐          ┌──────────────────────┐
  │ 1.0 Ideation │               │              │          │ Data Engineer Agent   │
  │ 2.0 Plan     │               │  Reads all   │          │                      │
  │ 3.0 Design   │───────────▶   │  activities  │────────▶ │ OWNS: 3.2, 4.3, 4.4 │
  │ 4.0 Build    │               │  Classifies  │          │ Skills: 7 core, 2 new│
  │ 5.0 Deploy   │               │  Designs     │          │ Tools: dbt, Git, SQL │
  │ 6.0 Operate  │               │              │          │ Workflow: 5 steps    │
  └──────────────┘               └──────────────┘          └──────────────────────┘
```


## The 8-Step Process

The Agent Builder follows an 8-step process, like building a house from blueprints:

### Step 1: Receive the Agent Role

You provide:
- **Role name** — e.g., "Data Engineer"
- **Primary responsibility** — e.g., "automates data pipeline development"
- **Phase scope** (optional) — e.g., "phases 3 and 4"

```
Think of it like: Telling an architect "I want a house for a family of 4
with a home office."
```

### Step 2: Locate the Delivery Model

The builder looks for your delivery model files — Markdown documents that describe
each activity in your team's workflow. It checks common locations:

```
docs/knowledge-base/delivery_model_pages_linked/
├── 0.0_Delivery_Model_Management.md    ← Index file
├── 1.1_Define_Business_Case.md
├── 2.1_Plan_Sprint.md
├── 3.2_Design_Data_Solution.md         ← Each activity is a file
├── 4.3_Develop_Data_Platform.md
└── ...
```

```
Think of it like: Finding the building code book before designing the house.
```

### Step 3: Analyse and Classify Activities

For each activity in the delivery model, the builder classifies how the agent
is involved:

| Classification | What It Means | Analogy |
|---------------|--------------|---------|
| **OWNS** | Primary responsible | You cook this meal |
| **CONTRIBUTES** | Helps but doesn't lead | You chop vegetables for someone else's dish |
| **CONSUMES** | Only receives output | You eat what someone else cooked |
| **OUT_OF_SCOPE** | No involvement | Not your kitchen |

**Example classification:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Activity ID │ Activity Name              │ Classification │ Rationale    │
├─────────────┼────────────────────────────┼────────────────┼──────────────┤
│ 3.2         │ Design Data Solution       │ OWNS           │ Data Engineer│
│             │                            │                │ responsible  │
│ 3.6         │ Plan Testing               │ CONSUMES       │ Receives     │
│             │                            │                │ test plan    │
│ 4.3         │ Develop Data Platform      │ OWNS           │ Builds the   │
│             │                            │                │ platform     │
│ 4.4         │ Develop Data Solution      │ OWNS           │ Writes the   │
│             │                            │                │ pipelines    │
│ 5.1         │ Release Management         │ OUT_OF_SCOPE   │ Release Lead │
│             │                            │                │ handles this │
└──────────────────────────────────────────────────────────────────────────┘
```

### Step 3.5: Evaluate Splitting (Should We Break This Into Smaller Agents?)

This is a critical decision point. If the agent has too many responsibilities,
it might work better as several smaller, focused agents.

```
Think of it like: Deciding whether to hire one general contractor or
three specialists (electrician, plumber, carpenter). Sometimes one
person can do it all. Sometimes you need a team.
```

The builder uses 7 criteria to decide — see the next section for details.

### Step 4: Derive Skills

The builder checks the skill catalogue to see what reusable capabilities already
exist, and proposes new ones for any gaps.

```
Think of it like: Checking what power tools you already have in the
garage before buying new ones. Don't buy a second drill if you already
have one.
```

### Step 5: Draft the Design Document

A 13-section Markdown document that fully describes the agent. This is the
blueprint. See "Understanding the Outputs" below for all 13 sections.

### Step 6: Draft the Agent Manifest

A YAML file that machines can read — it lists the agent's skills, tools,
knowledge base, and workflow phases in a structured format.

### Step 7: Confirm with User

Before writing any files, the builder presents a summary and asks for approval.
Nothing happens without your confirmation.

```
Think of it like: The architect showing you the floor plan and asking
"Does this look right?" before pouring the foundation.
```

### Step 8: Offer Configurator

After the design is complete, the builder offers to create a Configurator Agent
that can customize the design for specific use cases (projects).


## The 7 Splitting Criteria

When deciding whether to split one large agent into several smaller ones, the
builder evaluates 7 criteria. Here they are with real-world analogies:

### 1. Context Boundaries

**Question:** Do all activities share the same context (same codebase, same
standards, same domain)?

```
Restaurant analogy: Can one chef handle both the sushi bar and the
pizza oven? They use completely different ingredients, techniques, and
equipment. SPLIT if contexts are very different.
```

| Signal | Decision |
|--------|----------|
| All activities work with the same code and tools | KEEP |
| Activities span different codebases or domains | SPLIT |

### 2. Tool Permissions

**Question:** Can one set of credentials (one login, one service account)
handle everything?

```
Building analogy: Does the worker need keys to both the office and the
server room? If different security clearances are needed, it's cleaner
to have separate workers.
```

| Signal | Decision |
|--------|----------|
| Same tools and permissions needed | KEEP |
| Different tools or security levels required | SPLIT |

### 3. Independent Verification

**Question:** Does the work need to be reviewed by separate reviewers?

```
Banking analogy: The person who writes a check shouldn't also be the
person who approves it. If different review processes exist, separate
agents help maintain accountability.
```

| Signal | Decision |
|--------|----------|
| Same reviewer for all work | KEEP |
| Different review processes or approvers | SPLIT |

### 4. Parallelism Value

**Question:** Could the work run faster if done in parallel?

```
Moving house analogy: Can one person pack the kitchen while another
packs the bedroom? If the tasks are independent, parallel execution
helps. If task B needs task A's output, parallelism doesn't help.
```

| Signal | Decision |
|--------|----------|
| Tasks must happen in sequence (A then B then C) | KEEP |
| Tasks can run simultaneously | SPLIT |

### 5. Development and Test Ease

**Question:** Is the agent easier to develop and test if split?

```
Car repair analogy: Testing the engine separately from the brakes is
easier than testing the entire car at once. Smaller pieces = easier
quality assurance.
```

| Signal | Decision |
|--------|----------|
| Small scope, easy to test together | KEEP |
| Large scope, easier to test pieces separately | SPLIT |

### 6. Task Count (Strong Signal)

**Question:** How many core responsibilities does the agent have?

```
Rule of thumb:
  1-5 tasks  → Almost always KEEP as one agent
  6-8 tasks  → Borderline, check other criteria
  9+ tasks   → Strong signal to SPLIT
```

```
Juggling analogy: Most people can juggle 3-5 balls. Beyond 8, you're
dropping things. Same with agent responsibilities.
```

### 7. Team Scaling

**Question:** Would splitting let multiple developers work on the agent
in parallel?

```
Software team analogy: If 3 developers could each build one sub-agent
independently, that's faster than 3 developers waiting to take turns
on one big agent.
```

| Signal | Decision |
|--------|----------|
| One developer can handle everything | KEEP |
| Multiple developers would benefit from working in parallel | SPLIT |

### How the Score Works

Each criterion votes SPLIT or KEEP. The majority wins:

```
  Criterion               │ Vote
  ────────────────────────┼──────
  Context Boundaries      │ SPLIT
  Tool Permissions        │ SPLIT
  Independent Verification│ SPLIT
  Parallelism Value       │ KEEP
  Development & Test      │ SPLIT
  Task Count              │ SPLIT  (strong signal)
  Team Scaling            │ SPLIT  (strong signal)
  ────────────────────────┼──────
  Score: 5 SPLIT / 2 KEEP │ → SPLIT recommended
```


## Running the Agent Builder via Claude Code

In your Claude Code session:

```
You: Design a Data Engineer agent. The delivery model is at
     test-data/docs/

Claude: I'll bootstrap a Data Engineer agent design. Let me:

        Step 1: Role = Data Engineer, responsibility = "automates
                data pipeline development"

        Step 2: Checking delivery model at test-data/docs/...
                Found 15 activity files.

        Step 3: Classifying activities...
                [Shows classification table]

        Step 3.5: Evaluating splitting...
                  3 OWNS activities, score: KEEP_AS_ONE

        Step 4: Mapping skills... 5 existing, 2 new proposed

        Steps 5-6: Generating design document and manifest...

        Step 7: Here's what I'll create:
                - data_engineer_Agent_Design.md (13 sections)
                - data_engineer_agent-template.yaml

                Shall I write these files?
```


## Running the Agent Builder via AgentCore Harness

Run the AI-powered version in the AWS cloud:

```bash
# First, make sure the harness exists
uv run python -m agents.harness_agents.create_agent_builder

# Then invoke it
uv run python -m agent_builder.platforms.agentcore_harness.invoke_builder \
  "Data Engineer" \
  "automates data pipeline development" \
  "test-data/docs" \
  "arn:aws:bedrock-agentcore:us-west-2:981956186421:harness/agent_builder-Aa3Ai2hEop"
```


## Running the Agent Builder via GitHub Copilot CLI

The GitHub Copilot version works as a CLI-driven agent. You run commands in your
terminal and the agent uses the Python core modules to do the work.

```bash
# Locate the delivery model
cd data-sdlc-framework
python -c "
import sys; sys.path.insert(0, '.')
from agent_builder.core.analyser import DeliveryModelAnalyser
analyser = DeliveryModelAnalyser('test-data/docs')
info = analyser.locate_model()
print(f'Found: {info[\"found\"]}')
print(f'Activities: {info[\"activity_count\"]}')
for aid in info['activity_ids']:
    print(f'  {aid}')
"

# Run the splitting evaluation
python -c "
import sys; sys.path.insert(0, '.')
from agent_builder.core.splitter import evaluate_splitting
from agent_builder.core.models import AgentRole, ActivityClassification, InvolvementCode

role = AgentRole('Data Engineer', 'automates data pipeline development')
classifications = [
    ActivityClassification('3.2', 'Design Data Solution', InvolvementCode.OWNS, 'Primary responsible'),
    ActivityClassification('4.3', 'Develop Data Platform', InvolvementCode.OWNS, 'Builds platform'),
    ActivityClassification('4.4', 'Develop Data Solution', InvolvementCode.OWNS, 'Writes pipelines'),
]
result = evaluate_splitting(role, classifications)
print(f'Decision: {result.decision.value}')
print(f'Rationale: {result.rationale}')
print(f'Score: {result.split_score} split / {result.keep_score} keep')
"
```


## Understanding the Agent Builder Outputs

### The 13-Section Design Document

The design document is a comprehensive blueprint with these sections:

```
┌────────────────────────────────────────────────────────┐
│  AI Agent Design: Data Engineer                         │
│                                                         │
│  §1  Identity         Who is this agent?                │
│  §2  Responsibilities What does it do? (numbered list)  │
│  §3  Scope            In scope / Out of scope / Human   │
│  §4  Inputs           What does it receive?             │
│  §5  Outputs          What does it produce?             │
│  §6  Skills           Reusable capability modules       │
│  §7  Knowledge        What does it need to know?        │
│  §8  Tools            What systems does it use?         │
│  §9  Workflow          Step-by-step process              │
│  §10 Human Interaction When does a human step in?       │
│  §11 Handoffs         When does it pass work to others? │
│  §12 Evaluation       How do we measure quality?        │
│  §13 Constraints      Rules and guardrails              │
│                                                         │
│  ⚠️  Information Gaps  What's still unknown?            │
└────────────────────────────────────────────────────────┘
```

Sections marked `⚠️ NEEDS INFO` require human input — the builder flags everything
it couldn't determine from the delivery model alone.

### The Agent Manifest (YAML)

A machine-readable version of the design:

```yaml
agent:
  name: ""                          # Fill in per use case
  role: "data_engineer"
  version: "0.1.0-draft"

skills:
  active:                           # Always-on skills
    - "delivery_model_analysis"
    - "entity_extraction"
  inactive:                         # Activated by context
    - "graphify_analysis"           # Only for engineer roles

tools:
  - name: "dbt"
    purpose: "Data transformation"
  - name: "git"
    purpose: "Version control"

phases:
  - id: "3.2"
    display_name: "Design Data Solution"
    trigger: "start"
    active_skills: [...]
    human_gates: [...]
```

---

# Part 4: Working with AgentCore Harness

## What Is a Harness?

**Think of a Harness as a recipe card for an AI chef.**

You write the recipe card (system prompt, tools, model), hand it to the cloud kitchen
(AWS AgentCore), and they take care of everything else — hiring the chef (the AI
model), setting up the kitchen (compute), and running the meal service (handling
requests).

```
  Recipe Card (Harness Definition)
  ┌──────────────────────────────────────────────┐
  │  Name:   discovery_agent                      │
  │  Chef:   Claude Opus 4.6                      │
  │  Style:  Repository discovery specialist      │
  │                                               │
  │  Pantry (Tools):                              │
  │    1. walk_repository — find all files        │
  │    2. read_file — read a file's content       │
  │    3. ingest_entities — save to knowledge map │
  │    4. ingest_relationships — save connections  │
  │                                               │
  │  Instructions:                                │
  │    Walk the codebase, extract entities,       │
  │    build the knowledge graph.                 │
  └──────────────────────────────────────────────┘
```

You create this recipe once, and then invoke it as many times as you want.


## Creating Your Harness

We provide ready-made scripts that create (or update) the harnesses:

```bash
# Create both harnesses at once
uv run python -m agents.harness_agents.create_all

# Or create them individually:
uv run python -m agents.harness_agents.create_discovery_agent
uv run python -m agents.harness_agents.create_agent_builder

# With custom options:
uv run python -m agents.harness_agents.create_discovery_agent \
  --region us-east-1 \
  --role-arn arn:aws:iam::123456789:role/MyRole
```

The scripts are **idempotent** — running them twice doesn't create duplicates.
If the harness already exists, it updates it instead.

What happens when you run the script:

```
  ┌─────────────┐         ┌──────────────────────┐
  │  Your        │  1. Create / Update Harness     │
  │  Computer    │ ────────────────────────────▶    │
  │              │                                  │
  │              │  2. "Harness ID: abc123"         │  AWS AgentCore
  │              │ ◀────────────────────────────    │  Control Plane
  │              │                                  │
  │              │  3. Poll for READY status        │
  │              │ ────────────────────────────▶    │
  │              │                                  │
  │              │  4. "Status: READY"              │
  │              │ ◀────────────────────────────    │
  └─────────────┘                                  │
                          └──────────────────────┘
```


## Invoking a Harness

Once created, you invoke the harness to start a conversation with the AI:

```bash
# Discovery: scan a repository
uv run python -m discovery.invoke_harness /path/to/your/repo my-project

# Agent Builder: design an agent
uv run python -m agent_builder.platforms.agentcore_harness.invoke_builder \
  "Data Engineer" "automates pipelines" "/path/to/model" "arn:aws:...:harness/..."
```

### What Happens Under the Hood

A harness invocation is a **multi-turn conversation** between your code and the AI:

```
  Turn 1:
    You → AI:  "Discover the repository at /path/to/repo"
    AI  → You: "I need to walk the repo. Call walk_repository for me."

  Turn 2:
    You → AI:  [walk_repository results: 45 files found]
    AI  → You: "Good. Now read the first SQL file. Call read_file for me."

  Turn 3:
    You → AI:  [read_file results: CREATE TABLE customers...]
    AI  → You: "Found a DataAsset. Ingest this entity for me."

  Turn 4:
    You → AI:  [ingest_entities results: 1 ingested]
    AI  → You: "Now read the next file..."

  ... continues until done ...

  Turn N:
    AI  → You: "Discovery complete. Found 256 entities and 89 relationships."
```


## Inline Function Tools

**Inline function tools** are the heart of the harness pattern. They let the AI
request work that runs on YOUR computer, not in the cloud.

**Why?** Because:
- Your files are on your computer, not in AWS
- The AI can't directly access your filesystem
- Security: tools run with your permissions, not AWS's

```
Think of it like: A remote doctor (the AI) calling you on the phone
and asking you to take your own blood pressure and read the numbers
back. The doctor makes the decisions, but you do the physical actions.
```

Each harness has specific tools:

**Discovery Agent's 4 Tools:**

| Tool | What It Does | Analogy |
|------|-------------|---------|
| `walk_repository` | Lists and classifies all files | Librarian walking the shelves |
| `read_file` | Reads a file's content | Opening a book to read it |
| `ingest_entities` | Saves discovered entities | Writing a catalog card |
| `ingest_relationships` | Saves connections between entities | Drawing lines between cards |

**Agent Builder's 5 Tools:**

| Tool | What It Does | Analogy |
|------|-------------|---------|
| `locate_delivery_model` | Finds the process documents | Finding the building codes |
| `read_activity` | Reads one activity document | Reading one chapter |
| `evaluate_splitting` | Runs the 7-criteria check | Consulting the team about splitting work |
| `check_existing_skills` | Checks for duplicate skills | Checking the toolbox for existing tools |
| `render_design` | Generates the final documents | Printing the blueprints |


## Control Plane vs Data Plane

AWS AgentCore has two separate APIs. This confuses many people, so let's make it clear:

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                                                                  │
  │  CONTROL PLANE                     DATA PLANE                    │
  │  (The Manager)                     (The Worker)                  │
  │                                                                  │
  │  "Create things, configure         "Use things, do real work"    │
  │   things, manage things"                                         │
  │                                                                  │
  │  Client name:                      Client name:                  │
  │  bedrock-agentcore-control         bedrock-agentcore             │
  │                                                                  │
  │  What it does:                     What it does:                 │
  │  • Create harnesses                • Invoke harnesses            │
  │  • Update harnesses                • Send messages to agents     │
  │  • List harnesses                  • Execute code                │
  │  • Delete harnesses                • Write to memory stores      │
  │  • Create memory stores            • Call running agents         │
  │  • Create gateways                 • Search memory               │
  │                                                                  │
  └─────────────────────────────────────────────────────────────────┘
```

**In Python code:**

```python
import boto3

# CONTROL PLANE — for creating/managing (used once during setup)
control = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
control.create_harness(...)      # Create the recipe
control.update_harness(...)      # Update the recipe
control.get_harness(...)         # Check the status

# DATA PLANE — for running/using (used every time you invoke)
data = boto3.client('bedrock-agentcore', region_name='us-west-2')
data.invoke_harness(...)         # Ask the AI to do something
```

```
Restaurant analogy:
  Control Plane = The restaurant owner who designs the menu,
                  hires chefs, and sets up the kitchen
  Data Plane    = The waiter who takes orders and serves food
                  to customers
```

---

# Part 5: Testing

## Running the Test Suite

The project has 145 tests (71 for discovery, 74 for agent builder):

```bash
cd data-sdlc-framework

# Run ALL tests
uv run --with pytest pytest tests/ -v

# Run only discovery tests
uv run --with pytest pytest tests/test_discovery.py -v

# Run only agent builder tests
uv run --with pytest pytest tests/test_agent_builder.py -v

# Run a specific test
uv run --with pytest pytest tests/test_discovery.py::TestWalkRepository -v

# Run with short error output (easier to read)
uv run --with pytest pytest tests/ -v --tb=short
```


## What the Tests Cover

### Discovery Tests (71 tests)

| Test Group | Count | What It Tests |
|-----------|-------|--------------|
| Walk Repository | 12 | File classification (SQL, Python, Terraform, etc.) |
| Read File | 8 | Reading file content, handling errors |
| Classify File | 15 | Identifying file types from names/paths |
| Ingest Entities | 10 | Saving entities to the graph |
| Ingest Relationships | 10 | Saving connections, resolving references |
| Resolve References | 8 | Name-based entity lookup |
| Registry | 4 | Strategy selection |
| Claude Code Strategy | 2 | Claude Code adapter |
| Integration | 2 | End-to-end walk → ingest |

### Agent Builder Tests (74 tests)

| Test Group | Count | What It Tests |
|-----------|-------|--------------|
| Models | 10 | Data structures (AgentRole, classifications) |
| Analyser | 12 | Reading delivery model files |
| Splitter (Heuristic) | 10 | Splitting decisions with no LLM |
| Splitter (LLM) | 8 | Splitting decisions with LLM criteria |
| Skills | 10 | Skill catalogue, duplicate detection |
| Renderer (Design) | 10 | 13-section document generation |
| Renderer (Manifest) | 8 | YAML manifest generation |
| End-to-End | 6 | Full pipeline with real test-data |


## Using the Test-Data Folder

The `test-data/` folder is a sample repository that mimics a real data engineering
project. It contains:

```
test-data/
├── code/                           # Source code
│   ├── dbt/                        # dbt models, seeds, sources
│   │   ├── models/staging/         # Staging SQL models
│   │   ├── models/marts/           # Mart SQL models
│   │   ├── seeds/                  # Seed CSV data
│   │   └── dbt_project.yml         # dbt configuration
│   ├── ingestion/                  # Python ingestion scripts
│   │   └── ingest_*.py             # Data loading pipelines
│   └── spark/                      # Spark jobs
│       └── etl_pipeline.py         # ETL processing
│
├── infrastructure/                 # Infrastructure as Code
│   ├── terraform/                  # Terraform configs
│   │   ├── main.tf
│   │   └── variables.tf
│   └── docker/                     # Container definitions
│       ├── Dockerfile
│       └── docker-compose.yml
│
├── ci-cd/                          # CI/CD pipelines
│   └── github-actions/             # GitHub Actions workflows
│       ├── ci-pipeline.yml
│       ├── cd-staging.yml
│       ├── cd-production.yml
│       └── dbt-ci.yml
│
├── docs/                           # Project documentation
│   ├── 01-discovery/               # Business case, stakeholder analysis
│   ├── 02-requirements/            # Data & functional requirements
│   ├── 03-architecture/            # Solution & data architecture
│   ├── 04-design/                  # Pipeline & security design
│   ├── 05-development/             # Coding standards
│   ├── 06-testing/                 # Test strategy
│   ├── 08-deployment/              # Deployment guide
│   └── 10-transition-to-bau/       # Handover & decommission
│
└── agent-demo-de/                  # Agent demo files
```

This test data is used by both the automated tests and for manual experimentation.
You can run discovery against it to see real results without needing your own
repository.

---

# Part 6: Common Tasks (Cookbook)

## I Want to Scan My Repository

**Goal:** Build a knowledge graph of your codebase.

### Option A: Quick Local Scan (No AWS Needed)

```bash
cd data-sdlc-framework

uv run python -c "
from discovery.tools.walk import walk_repository
result = walk_repository('/path/to/your/repo')
print(f'Found {result[\"total_candidates\"]} candidate files')
for kind, count in sorted(result['by_source_kind'].items()):
    print(f'  {kind}: {count}')
print()
print('Technical files:')
for f in result['technical'][:10]:
    print(f'  {f[\"path\"]} ({f[\"source_kind\"]})')
if len(result['technical']) > 10:
    print(f'  ... and {len(result[\"technical\"]) - 10} more')
"
```

### Option B: Full AI-Powered Scan (AWS Required)

```bash
# 1. Create the harness (first time only)
uv run python -m agents.harness_agents.create_discovery_agent

# 2. Run the discovery
uv run python -m discovery.invoke_harness /path/to/your/repo my-project
```

### Option C: Interactive Scan with Claude Code

In Claude Code:

```
You: Run discovery against /path/to/my/repo using the repository-discovery skill
```


## I Want to Design a New Agent

**Goal:** Generate a design document for a new AI agent role.

### Step 1: Prepare Your Delivery Model

Make sure you have Markdown files describing your delivery activities:

```bash
ls /path/to/your/delivery-model/
# Should see files like: 3.2_Design_Data_Solution.md, 4.3_Develop_Platform.md
```

### Step 2: Choose a Platform

**Claude Code (recommended for first time):**

```
You: Bootstrap a Release Lead agent. The delivery model is at
     /path/to/your/delivery-model/

     The Release Lead's primary responsibility is "manages release
     planning, deployment coordination, and go-live readiness"
```

**AgentCore Harness:**

```bash
uv run python -m agent_builder.platforms.agentcore_harness.invoke_builder \
  "Release Lead" \
  "manages release planning, deployment coordination" \
  "/path/to/your/delivery-model" \
  "arn:aws:bedrock-agentcore:us-west-2:YOUR_ACCOUNT:harness/agent_builder-XXXXX"
```

**GitHub Copilot CLI:**

```bash
python -c "
import sys; sys.path.insert(0, '.')
from agent_builder.core.analyser import DeliveryModelAnalyser
from agent_builder.core.models import AgentRole
analyser = DeliveryModelAnalyser('/path/to/your/delivery-model')
info = analyser.locate_model()
print(f'Found {info[\"activity_count\"]} activities')
# ... follow the 8-step process using core modules
"
```

### Step 3: Review the Output

Check the generated files:

```bash
ls agent-builder/agent-designs/
# release_lead_Agent_Design.md
# release_lead_agent-template.yaml
```

Look for `⚠️ NEEDS INFO` markers — these are gaps you need to fill.


## I Want to Add a New Discovery Strategy

**Goal:** Add a new way to run discovery (e.g., a custom LLM or external service).

### Step 1: Create the Strategy File

```bash
# Create a new file in discovery/strategies/
touch discovery/strategies/my_strategy.py
```

### Step 2: Implement the Protocol

```python
# discovery/strategies/my_strategy.py
from discovery.strategy import DiscoveryStrategy

class MyStrategy(DiscoveryStrategy):
    """My custom discovery strategy."""

    def __init__(self, **kwargs):
        self.config = kwargs

    def discover(self, repository_root: str, project_id: str) -> dict:
        # Use the shared tools
        from discovery.tools.walk import walk_repository
        from discovery.tools.read import read_file
        from discovery.tools.ingest import ingest_entities, get_graph_state

        # Walk
        walk_result = walk_repository(repository_root)

        # Read and extract (your custom logic here)
        entities = []
        for f in walk_result['technical']:
            content = read_file(repository_root, f['path'])
            # ... your extraction logic ...
            entities.append({...})

        # Ingest
        ingest_entities(project_id, entities)

        return get_graph_state(project_id)
```

### Step 3: Register in the Registry

Edit `discovery/registry.py`:

```python
STRATEGIES["my_strategy"] = {
    "class": "discovery.strategies.my_strategy.MyStrategy",
    "description": "My custom strategy for ...",
    "requires": ["whatever it needs"],
}
```

### Step 4: Use It

```python
from discovery.registry import get_strategy
strategy = get_strategy("my_strategy", config_param="value")
result = strategy.discover("/path/to/repo", "my-project")
```


## I Want to Update the Harness

**Goal:** Change the system prompt, tools, or model of an existing harness.

### Step 1: Edit the Source

For the Discovery Agent, edit one of:
- `discovery/skills/repository-discovery.md` — to change the instructions
- `agents/harness_agents/create_discovery_agent.py` — to change tools or model

For the Agent Builder, edit one of:
- `prompts/agent-builder.prompt.md` — to change the instructions
- `agents/harness_agents/create_agent_builder.py` — to change tools or model

### Step 2: Re-Run the Create Script

```bash
# This will detect the existing harness and UPDATE it
uv run python -m agents.harness_agents.create_discovery_agent

# Or update both
uv run python -m agents.harness_agents.create_all
```

The script automatically:
1. Tries to create (if new)
2. If it already exists, updates it instead
3. Waits for the harness to reach READY status

---

# Part 7: Troubleshooting

## Common Errors and What They Mean

### "No credentials found" / "Unable to locate credentials"

```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**What it means:** Your AWS credentials are not set up.
**How to fix:**

```bash
# Check if credentials exist
aws sts get-caller-identity

# If that fails, configure them:
aws configure
```

### "AccessDeniedException"

```
botocore.exceptions.ClientError: AccessDeniedException: User is not authorized
```

**What it means:** Your AWS user doesn't have permission to use AgentCore.
**How to fix:** Ask your AWS administrator to grant you `bedrock-agentcore:*`
permissions.

### "ConflictException" when creating a harness

```
ConflictException: Harness with name 'discovery_agent' already exists
```

**What it means:** The harness already exists (this is handled automatically by
the create scripts). If you see this in custom code, use `update_harness` instead
of `create_harness`.

### "ReadTimeoutError" during harness invocation

```
urllib3.exceptions.ReadTimeoutError: Read timed out
```

**What it means:** The AI took too long to respond (usually because it's reading
many large files). This can happen with very large repositories.
**How to fix:**
- Use the **quick** discovery mode for large repos
- Break the scan into smaller parts (scan one folder at a time)
- Increase the read timeout in your boto3 config:

```python
from botocore.config import Config
config = Config(read_timeout=300)  # 5 minutes instead of default
client = boto3.client("bedrock-agentcore", config=config)
```

### "Unknown tool: xxx"

```
{"error": "Unknown tool: my_tool_name"}
```

**What it means:** The AI tried to call a tool that doesn't exist in your
tool dispatcher. Check that all tool names in your harness definition match
the tool names in your `_execute_tool()` function.

### "dangling_source" or "dangling_target" in relationship ingestion

```
{"kind": "dangling_source", "detail": "DEPENDS_ON: source 'my_entity' not in graph"}
```

**What it means:** A relationship references an entity that hasn't been ingested yet.
This usually happens when:
- The entity name doesn't match exactly (case, spaces, underscores)
- The entity wasn't ingested in a previous step

The system uses **fuzzy matching** (`_resolve_ref()`) to handle common variations,
but if the name is very different, it won't match.

### "harness in FAILED status"

**What it means:** Something went wrong during harness creation (usually an invalid
model ID or missing IAM role).
**How to fix:**
- Check the model ID format: should be `global.anthropic.claude-opus-4-6-v1`
- Check the IAM role ARN exists and has the right permissions
- Try deleting and recreating the harness

### Module import errors

```
ModuleNotFoundError: No module named 'agent_builder'
```

**What it means:** Python can't find the agent-builder module.
**How to fix:** The project uses a symlink `agent_builder → agent-builder` because
Python can't import from hyphenated directory names. Make sure the symlink exists:

```bash
ls -la agent_builder  # Should show: agent_builder -> agent-builder
# If missing:
ln -s agent-builder agent_builder
```

---

# Part 8: Glossary

All technical terms used in this manual, defined in plain English.

| Term | Definition |
|------|-----------|
| **Activity** | One step in a delivery model (e.g., "Design Data Solution" or "Plan Testing") |
| **Agent** | An AI assistant designed for a specific role (like a virtual team member) |
| **Agent Builder** | The tool that reads delivery models and designs new agents |
| **AgentCore** | Amazon's cloud service for running AI agents |
| **API** | Application Programming Interface — a way for programs to talk to each other |
| **ARN** | Amazon Resource Name — a unique ID for any resource in AWS (like a street address) |
| **AWS** | Amazon Web Services — cloud computing platform |
| **boto3** | The Python library for talking to AWS services |
| **CI/CD** | Continuous Integration / Continuous Deployment — automated build and release pipelines |
| **Classification** | The process of categorizing how an agent relates to an activity (OWNS, CONTRIBUTES, CONSUMES, OUT_OF_SCOPE) |
| **Claude Code** | Anthropic's CLI tool for using Claude in your terminal or IDE |
| **Claude Opus 4.6** | The AI model used by the harnesses — large, capable, thorough |
| **Confidence Score** | A number from 0 to 1 indicating how sure the system is about a finding |
| **CONSUMES** | An agent receives output from an activity but doesn't do the work |
| **CONTRIBUTES** | An agent participates in an activity but isn't the primary owner |
| **Control Plane** | The AWS API for creating and managing resources (the "manager") |
| **Data Plane** | The AWS API for using resources (the "worker") |
| **DataAsset** | A table, view, dataset, file, or other data resource |
| **dbt** | "data build tool" — a popular tool for transforming data in warehouses |
| **Delivery Model** | A structured framework describing how a team delivers software |
| **Delta Discovery** | Scanning only files that changed since the last scan |
| **Discovery Agent** | The tool that scans a codebase and builds a knowledge graph |
| **Entity** | Anything the Discovery Agent identifies — a pipeline, table, document, etc. |
| **Entity ID** | A unique identifier for an entity (e.g., `pipeline:atlas_daily_dbt`) |
| **EvidenceRequirement** | Proof needed to pass a quality gate |
| **Gate** | A quality checkpoint that must pass before work can continue |
| **GitHub Copilot** | GitHub's AI coding assistant |
| **Harness** | An AgentCore resource that defines an AI agent's model, tools, and instructions |
| **Heuristic** | A rule-of-thumb approach (vs. asking the AI to decide) |
| **Idempotent** | Running something twice produces the same result as running it once (safe to repeat) |
| **INFERRED** | An entity found by pattern matching, not directly stated in the code |
| **Infrastructure** | Servers, containers, cloud resources, networking — the "plumbing" |
| **Inline Function Tool** | A tool that runs on your machine, not in the cloud |
| **Ingestion** | The process of saving discovered entities and relationships to the graph |
| **Knowledge Graph** | A structured map showing entities and how they relate to each other |
| **Layer** | Skill classification: L1=foundation, L2=core (always active), L3=conditional |
| **Manifest** | A YAML file describing an agent's configuration in machine-readable format |
| **OBSERVED** | An entity found directly and explicitly in the code |
| **OUT_OF_SCOPE** | An activity that has no relevance to the agent being designed |
| **OWNS** | An agent is the primary responsible party for an activity |
| **Pipeline** | An automated workflow that moves or transforms data |
| **Provenance** | Where and how an entity was discovered (OBSERVED or INFERRED) |
| **Relationship** | A connection between two entities (e.g., "Pipeline PRODUCES DataAsset") |
| **Registry** | A lookup table of available strategies |
| **Renderer** | Code that generates the final output documents |
| **SchemaDefinition** | A description of data structure (column names, types, constraints) |
| **Slug** | A URL/ID-safe version of a name: "Data Engineer" → "data_engineer" |
| **Source Kind** | The type of file: SQL, Python, Terraform, Markdown, etc. |
| **Splitting** | Breaking one large agent into several smaller, focused agents |
| **Strategy** | A pattern for how discovery runs (local, harness, runtime, claude-code) |
| **Symlink** | A shortcut file that points to another file or directory |
| **System Prompt** | Instructions given to an AI that define its role and behavior |
| **Task** | A work item or action item found in project documentation |
| **Tool** | A function that an AI agent can call to perform an action |
| **uv** | A fast Python package manager and virtual environment tool |
| **YAML** | A human-readable data format used for configuration files |

---

## What's Next?

Now that you understand the framework, here are suggested next steps:

1. **Run the tests** to verify everything works in your environment
2. **Scan the test-data** repository to see discovery in action
3. **Try designing an agent** using the Agent Builder
4. **Scan your own repository** to build a real knowledge graph
5. **Create a harness** and try the cloud-powered version

If you get stuck, check the [Troubleshooting](#part-7-troubleshooting) section or
ask for help in your team's support channel.

---

*This manual was generated for the Data SDLC Framework project.*
*For the latest version, check the `docs/` folder in the repository.*
