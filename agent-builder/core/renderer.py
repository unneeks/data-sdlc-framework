"""Render the two output artefacts — design document and agent manifest."""

from __future__ import annotations

from typing import Any

from agent_builder.core.models import AgentDesign


def render_design_document(design: AgentDesign) -> str:
    """Render the 13-section agent design Markdown document."""
    role = design.role
    sections = []

    sections.append(f"# AI Agent Design: {role.role_name}\n")
    sections.append(f"**Status:** DRAFT")
    sections.append(f"**Date:** {design.generated_date}")
    sections.append(f"**Derived from:** Delivery Model Framework — `{design.delivery_model_root}`")
    sections.append(f"**Agent Role ID:** `{role.role_id}`\n")
    sections.append("> Fields marked ⚠️ NEEDS INFO require confirmation before this design is finalised.\n")
    sections.append("---\n")

    # §1 Identity
    sections.append("## 1. Identity\n")
    sections.append(f"- **Role:** {role.role_name}")
    sections.append(f"- **Role ID:** `{role.role_id}`")
    sections.append(f"- **Primary Responsibility:** {role.primary_responsibility}")
    if role.phase_scope:
        sections.append(f"- **Phase Scope:** {', '.join(role.phase_scope)}")
    sections.append("")

    # §2 Responsibilities
    sections.append("## 2. Responsibilities\n")
    if design.responsibilities:
        for i, r in enumerate(design.responsibilities, 1):
            auto = "🤖" if r.get("automatable", True) else "👤"
            citation = f" *(source: {r['source']})*" if "source" in r else ""
            sections.append(f"{i}. {auto} {r.get('name', r.get('description', ''))}{citation}")
    else:
        sections.append("⚠️ NEEDS INFO — No responsibilities extracted yet")
    sections.append("")

    # §3 Scope
    sections.append("## 3. Scope\n")
    sections.append("### In Scope\n")
    for c in design.owns_activities:
        sections.append(f"- {c.activity_id} {c.activity_name} *(OWNS)*")
    for c in design.contributes_activities:
        sections.append(f"- {c.activity_id} {c.activity_name} *(CONTRIBUTES)*")
    sections.append("")
    sections.append("### Out of Scope\n")
    oos = [c for c in design.classifications if c.classification.value == "OUT_OF_SCOPE"]
    for c in oos[:5]:
        sections.append(f"- {c.activity_id} {c.activity_name}")
    sections.append("")
    sections.append("### Human-Reserved Decisions\n")
    human_decisions = [d for d in design.decisions if d.get("human_reserved")]
    if human_decisions:
        for d in human_decisions:
            sections.append(f"- ▶ HUMAN GATE: {d.get('name', '')}")
    else:
        sections.append("⚠️ NEEDS INFO — Human-reserved decisions not yet identified")
    sections.append("")

    # §4 Inputs
    sections.append("## 4. Inputs\n")
    sections.append("| Input | Source | Mandatory |")
    sections.append("|---|---|---|")
    for inp in design.inputs:
        m = "Yes" if inp.get("mandatory", True) else "Optional"
        sections.append(f"| {inp.get('name', '')} | {inp.get('source', '')} | {m} |")
    if not design.inputs:
        sections.append("| ⚠️ NEEDS INFO | — | — |")
    sections.append("")

    # §5 Outputs
    sections.append("## 5. Outputs\n")
    sections.append("| Output | Consuming Activity |")
    sections.append("|---|---|")
    for out in design.outputs:
        sections.append(f"| {out.get('name', '')} | {out.get('consuming_activity', '')} |")
    if not design.outputs:
        sections.append("| ⚠️ NEEDS INFO | — |")
    sections.append("")

    # §6 Skills
    sections.append("## 6. Skills\n")
    for s in design.skills:
        tag = "existing" if s.is_existing else "new"
        sections.append(f"- `{s.skill_id}` (L{s.layer}, {tag}): {s.description}")
        for r in s.responsibilities_covered:
            sections.append(f"  - covers: {r}")
    if not design.skills:
        sections.append("⚠️ NEEDS INFO — Skills not yet mapped")
    sections.append("")

    # §7 Knowledge
    sections.append("## 7. Knowledge\n")
    for k in design.knowledge:
        sections.append(f"- **{k.get('name', '')}** ({k.get('type', '')})")
    if not design.knowledge:
        sections.append("⚠️ NEEDS INFO — Knowledge sources not yet identified")
    sections.append("")

    # §8 Tools
    sections.append("## 8. Tools\n")
    sections.append("| Tool | Purpose |")
    sections.append("|---|---|")
    for t in design.tools:
        sections.append(f"| {t.get('name', '')} | {t.get('purpose', '')} |")
    if not design.tools:
        sections.append("| ⚠️ NEEDS INFO | — |")
    sections.append("")

    # §9 Workflow
    sections.append("## 9. Workflow\n")
    for i, step in enumerate(design.workflow_steps, 1):
        gate = " ▶ HUMAN GATE" if step.get("human_gate") else ""
        sections.append(f"{i}. **{step.get('name', '')}**{gate}")
        if step.get("description"):
            sections.append(f"   {step['description']}")
    if not design.workflow_steps:
        sections.append("⚠️ NEEDS INFO — Workflow not yet defined")
    sections.append("")

    # §10 Human Interaction
    sections.append("## 10. Human Interaction\n")
    if human_decisions:
        for d in human_decisions:
            sections.append(f"- **{d.get('name', '')}**: {d.get('rationale', '')}")
    else:
        sections.append("⚠️ NEEDS INFO")
    sections.append("")

    # §11 Handoffs
    sections.append("## 11. Handoffs\n")
    sections.append("| From/To | Agent/Role | Trigger | Artefact |")
    sections.append("|---|---|---|---|")
    for h in design.handoffs:
        sections.append(f"| {h.get('direction', '')} | {h.get('agent', '')} | {h.get('trigger', '')} | {h.get('artefact', '')} |")
    if not design.handoffs:
        sections.append("| ⚠️ NEEDS INFO | — | — | — |")
    sections.append("")

    # §12 Evaluation Metrics
    sections.append("## 12. Evaluation Metrics\n")
    for m in design.evaluation_metrics:
        sections.append(f"- {m.get('name', '')}: {m.get('metric', '')}")
    if not design.evaluation_metrics:
        sections.append("⚠️ NEEDS INFO")
    sections.append("")

    # §13 Constraints & Guardrails
    sections.append("## 13. Constraints & Guardrails\n")
    for c in design.constraints:
        sections.append(f"- {c}")
    if not design.constraints:
        sections.append("⚠️ NEEDS INFO")
    sections.append("")

    # Information Gaps Summary
    sections.append("---\n")
    sections.append("## ⚠️ Summary of Information Gaps\n")
    if design.information_gaps:
        for gap in design.information_gaps:
            sections.append(f"- {gap}")
    else:
        sections.append("No information gaps identified.")

    return "\n".join(sections)


def render_agent_manifest(design: AgentDesign) -> str:
    """Render the agent-template.yaml starter manifest."""
    role = design.role
    lines = []

    lines.append(f"# Agent Manifest Starter — {role.role_name}")
    lines.append(f"# Derived from: Delivery Model Framework + {role.role_id}_Agent_Design.md")
    lines.append("# Schema version: 1.0.0")
    lines.append("# Status: DRAFT — populate per use case via Configurator\n")

    lines.append("agent:")
    lines.append('  name: ""')
    lines.append(f'  role: "{role.role_id}"')
    lines.append('  version: "0.1.0-draft"')
    lines.append('  generated_at: ""')
    lines.append('  generated_by: "agent-builder"')
    lines.append('  usecase_id: ""')
    lines.append('  context_object: "context.yaml"\n')

    lines.append("skills:")
    if design.skills:
        active = [s for s in design.skills if s.layer == 2]
        inactive = [s for s in design.skills if s.layer == 3]
        lines.append("  active:")
        for s in active:
            lines.append(f'    - "{s.skill_id}"')
        lines.append("  inactive:")
        for s in inactive:
            lines.append(f'    - "{s.skill_id}"  # applicable_when: {s.applicable_when}')
    else:
        lines.append("  active: []")
        lines.append("  inactive: []")
    lines.append("")

    lines.append("tools:")
    for t in design.tools:
        lines.append(f"  - name: \"{t.get('name', '')}\"")
        lines.append(f"    purpose: \"{t.get('purpose', '')}\"")
    if not design.tools:
        lines.append("  []  # Populate from agent design §8")
    lines.append("")

    lines.append("knowledge_base:")
    for c in design.owns_activities:
        lines.append(f"  - path: \"{c.source_file}\"")
        lines.append(f"    type: delivery_model")
        lines.append(f"    activity: \"{c.activity_id} {c.activity_name}\"")
    lines.append("")

    lines.append("phases:")
    for i, c in enumerate(design.owns_activities):
        lines.append(f"  - id: \"{c.activity_id}\"")
        lines.append(f"    display_name: \"{c.activity_name}\"")
        lines.append(f"    trigger: \"{'start' if i == 0 else 'previous_phase_complete'}\"")
        lines.append(f"    instruction_file: \"phases/{c.activity_id.replace('.', '_')}.md\"")
        lines.append(f"    entry_condition: \"TBD\"")
        lines.append(f"    active_skills: []")
        lines.append(f"    human_gates: []")
        lines.append(f"    outputs: []")
        lines.append(f"    exit_condition: \"TBD\"")
        next_phase = design.owns_activities[i + 1].activity_id if i + 1 < len(design.owns_activities) else "end"
        lines.append(f"    next_phase: \"{next_phase}\"")
    lines.append("")

    lines.append("constraints:")
    for c in design.constraints:
        lines.append(f'  - "{c}"')
    if not design.constraints:
        lines.append("  []  # Derive from agent design §13")

    return "\n".join(lines)
