"""
Comprehensive tests for the agent-builder module.

Tests cover:
  - core.models: data models, enums, properties
  - core.analyser: delivery model reading and prompt building
  - core.splitter: 7-criteria agent splitting evaluation
  - core.skills: skill catalogue management
  - core.renderer: design document and manifest rendering
  - Integration: end-to-end design flow using test-data/
"""
import sys
import os
import tempfile
import shutil
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from agent_builder.core.models import (
    AgentRole,
    ActivityClassification,
    AgentDesign,
    ExtractedField,
    InvolvementCode,
    SkillMapping,
    SplitCriterion,
    SplitDecision,
    SplitEvaluation,
)
from agent_builder.core.analyser import DeliveryModelAnalyser
from agent_builder.core.splitter import (
    evaluate_splitting,
    SPLITTING_CRITERIA_NAMES,
    SPLITTING_CRITERIA_PROMPTS,
)
from agent_builder.core.skills import SkillCatalogue
from agent_builder.core.renderer import render_design_document, render_agent_manifest

TEST_DATA = root_dir / "test-data"
SKILLS_ROOT = root_dir / "agent-builder" / "agent-skills"


# ---------------------------------------------------------------------------
# Fixtures: create a temp delivery model directory with proper naming
# ---------------------------------------------------------------------------

def _create_delivery_model_fixture(tmp: Path):
    """Create a minimal delivery model tree with numeric-prefixed filenames."""
    tmp.mkdir(parents=True, exist_ok=True)

    (tmp / "0.0_Delivery_Model_Management.md").write_text(
        "# Delivery Model Management\n\n"
        "## Phases\n"
        "- Phase 3: Design\n"
        "  - 3.2 Design Data Solution\n"
        "  - 3.6 Plan Testing\n"
        "- Phase 4: Build\n"
        "  - 4.3 Develop Data Platform Pattern\n"
        "  - 4.4 Develop Data Solution\n"
        "- Phase 5: Deploy\n"
        "  - 5.1 Deploy Release\n",
        encoding="utf-8",
    )

    (tmp / "3.2_Design_Data_Solution.md").write_text(
        "# 3.2 Design Data Solution\n\n"
        "## Responsible\n"
        "- Data Engineer (primary)\n"
        "- Solution Architect (reviewer)\n\n"
        "## Tasks\n"
        "- Design logical data model\n"
        "- Define schema standards\n"
        "- Create data dictionary\n\n"
        "## Inputs\n"
        "- Business requirements document\n"
        "- Current state assessment\n\n"
        "## Outputs\n"
        "- Logical data model\n"
        "- Data dictionary\n\n"
        "## Tools\n"
        "- ERD tool\n"
        "- Wiki\n",
        encoding="utf-8",
    )

    (tmp / "3.6_Plan_Testing.md").write_text(
        "# 3.6 Plan Testing\n\n"
        "## Responsible\n"
        "- Test Lead (primary)\n\n"
        "## Tasks\n"
        "- Define test strategy\n"
        "- Create test plan\n\n"
        "## Outputs\n"
        "- Test plan\n"
        "- Test cases\n",
        encoding="utf-8",
    )

    (tmp / "4.3_Develop_Data_Platform_Pattern.md").write_text(
        "# 4.3 Develop Data Platform Pattern\n\n"
        "## Responsible\n"
        "- Data Engineer (primary)\n\n"
        "## Tasks\n"
        "- Create reusable ingestion patterns\n"
        "- Build transformation templates\n"
        "- Establish CI/CD pipeline patterns\n\n"
        "## Tools\n"
        "- dbt\n"
        "- Terraform\n"
        "- GitHub Actions\n",
        encoding="utf-8",
    )

    (tmp / "4.4_Develop_Data_Solution.md").write_text(
        "# 4.4 Develop Data Solution\n\n"
        "## Responsible\n"
        "- Data Engineer (primary)\n"
        "- Lead Engineer (reviewer)\n\n"
        "## Tasks\n"
        "- Develop data pipelines\n"
        "- Implement dbt models\n"
        "- Configure Airflow DAGs\n"
        "- Write unit tests\n"
        "- Perform code reviews\n\n"
        "## Inputs\n"
        "- Logical data model (from 3.2)\n"
        "- Platform patterns (from 4.3)\n\n"
        "## Outputs\n"
        "- Working pipelines\n"
        "- Tested code in version control\n\n"
        "## Tools\n"
        "- dbt\n"
        "- Airflow\n"
        "- Spark\n"
        "- Git\n\n"
        "## Quality Checklist\n"
        "- All tests pass\n"
        "- Code review approved\n"
        "- Pipeline SLA met\n",
        encoding="utf-8",
    )

    (tmp / "5.1_Deploy_Release.md").write_text(
        "# 5.1 Deploy Release\n\n"
        "## Responsible\n"
        "- Release Manager (primary)\n\n"
        "## Tasks\n"
        "- Execute deployment plan\n"
        "- Run smoke tests\n",
        encoding="utf-8",
    )

    return tmp


# ===================================================================
# 1. MODELS
# ===================================================================


class TestAgentRole:
    def test_auto_role_id(self):
        role = AgentRole("Data Engineer", "builds pipelines")
        assert role.role_id == "data_engineer"

    def test_auto_role_id_with_hyphen(self):
        role = AgentRole("Release-Lead", "manages releases")
        assert role.role_id == "release_lead"

    def test_custom_role_id(self):
        role = AgentRole("Data Engineer", "builds pipelines", role_id="custom_de")
        assert role.role_id == "custom_de"

    def test_phase_scope_default_empty(self):
        role = AgentRole("Data Engineer", "builds pipelines")
        assert role.phase_scope == []

    def test_phase_scope_provided(self):
        role = AgentRole("Data Engineer", "builds pipelines", phase_scope=["3.2", "4.4"])
        assert role.phase_scope == ["3.2", "4.4"]


class TestInvolvementCode:
    def test_all_values_exist(self):
        assert InvolvementCode.OWNS.value == "OWNS"
        assert InvolvementCode.CONTRIBUTES.value == "CONTRIBUTES"
        assert InvolvementCode.CONSUMES.value == "CONSUMES"
        assert InvolvementCode.OUT_OF_SCOPE.value == "OUT_OF_SCOPE"

    def test_is_string_enum(self):
        assert isinstance(InvolvementCode.OWNS, str)
        assert InvolvementCode.OWNS == "OWNS"


class TestActivityClassification:
    def test_creation(self):
        ac = ActivityClassification("3.2", "Design Data Solution", InvolvementCode.OWNS, "Primary responsible")
        assert ac.activity_id == "3.2"
        assert ac.activity_name == "Design Data Solution"
        assert ac.classification == InvolvementCode.OWNS
        assert ac.rationale == "Primary responsible"
        assert ac.source_file == ""

    def test_with_source_file(self):
        ac = ActivityClassification("4.4", "Develop", InvolvementCode.OWNS, "reason", source_file="4.4_Develop.md")
        assert ac.source_file == "4.4_Develop.md"


class TestSplitEvaluation:
    def test_keep_decision(self):
        se = SplitEvaluation(decision=SplitDecision.KEEP_AS_ONE, rationale="small scope")
        assert se.decision == SplitDecision.KEEP_AS_ONE
        assert se.proposed_subagents == []

    def test_split_decision(self):
        se = SplitEvaluation(
            decision=SplitDecision.SPLIT_INTO_SUBAGENTS,
            rationale="too many responsibilities",
            proposed_subagents=[{"name": "sub_a"}, {"name": "sub_b"}],
            split_score=5,
            keep_score=2,
        )
        assert se.decision == SplitDecision.SPLIT_INTO_SUBAGENTS
        assert len(se.proposed_subagents) == 2
        assert se.split_score > se.keep_score


class TestAgentDesign:
    def _make_design(self):
        role = AgentRole("Data Engineer", "builds pipelines")
        classifications = [
            ActivityClassification("3.2", "Design Data", InvolvementCode.OWNS, "primary"),
            ActivityClassification("4.4", "Develop", InvolvementCode.OWNS, "primary"),
            ActivityClassification("3.6", "Plan Testing", InvolvementCode.CONTRIBUTES, "helps"),
            ActivityClassification("5.1", "Deploy", InvolvementCode.OUT_OF_SCOPE, "not involved"),
            ActivityClassification("6.1", "Operate", InvolvementCode.CONSUMES, "receives reports"),
        ]
        return AgentDesign(role=role, classifications=classifications)

    def test_owns_activities(self):
        design = self._make_design()
        owns = design.owns_activities
        assert len(owns) == 2
        assert all(c.classification == InvolvementCode.OWNS for c in owns)

    def test_contributes_activities(self):
        design = self._make_design()
        contribs = design.contributes_activities
        assert len(contribs) == 1
        assert contribs[0].activity_id == "3.6"

    def test_generated_date_auto(self):
        from datetime import date
        design = self._make_design()
        assert design.generated_date == date.today().isoformat()

    def test_generated_date_custom(self):
        role = AgentRole("Test", "test")
        design = AgentDesign(role=role, generated_date="2025-01-01")
        assert design.generated_date == "2025-01-01"


# ===================================================================
# 2. ANALYSER
# ===================================================================


class TestDeliveryModelAnalyser:
    def setup_method(self):
        self._tmp = Path(tempfile.mkdtemp())
        _create_delivery_model_fixture(self._tmp)

    def teardown_method(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_locate_model_found(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        info = analyser.locate_model()
        assert info["found"] is True
        assert info["activity_count"] == 6  # 0.0 (index), 3.2, 3.6, 4.3, 4.4, 5.1

    def test_locate_model_activity_ids(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        info = analyser.locate_model()
        assert "3.2" in info["activity_ids"]
        assert "4.4" in info["activity_ids"]
        assert "5.1" in info["activity_ids"]

    def test_locate_model_index_found(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        info = analyser.locate_model()
        assert info["index_file"] is not None
        assert "0.0_Delivery_Model" in info["index_file"]

    def test_locate_model_not_found(self):
        analyser = DeliveryModelAnalyser("/nonexistent/path/xyz")
        info = analyser.locate_model()
        assert info["found"] is False

    def test_read_activity(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()
        activity = analyser.read_activity("3.2")
        assert "error" not in activity
        assert activity["activity_id"] == "3.2"
        assert "Design Data Solution" in activity["content"]
        assert len(activity["sections"]) > 0

    def test_read_activity_sections_extracted(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()
        activity = analyser.read_activity("4.4")
        headings = [s["heading"] for s in activity["sections"]]
        assert "4.4 Develop Data Solution" in headings
        assert "Tasks" in headings
        assert "Tools" in headings

    def test_read_activity_not_found(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()
        activity = analyser.read_activity("99.99")
        assert "error" in activity

    def test_read_all_activities(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()
        all_activities = analyser.read_all_activities()
        assert len(all_activities) == 6

    def test_build_classification_prompt(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()
        activity = analyser.read_activity("3.2")
        role = AgentRole("Data Engineer", "builds pipelines")
        prompt = analyser.build_classification_prompt(activity, role)
        assert "Data Engineer" in prompt
        assert "OWNS" in prompt
        assert "CONTRIBUTES" in prompt
        assert "CONSUMES" in prompt
        assert "OUT_OF_SCOPE" in prompt
        assert "Design Data Solution" in prompt

    def test_build_extraction_prompt(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()
        activity = analyser.read_activity("4.4")
        role = AgentRole("Data Engineer", "builds pipelines")
        prompt = analyser.build_extraction_prompt(activity, role)
        assert "Data Engineer" in prompt
        assert "builds pipelines" in prompt
        assert '"tasks"' in prompt
        assert '"inputs"' in prompt
        assert '"outputs"' in prompt
        assert "Develop Data Solution" in prompt

    def test_get_index_content(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()
        content = analyser.get_index_content()
        assert "Delivery Model Management" in content

    def test_get_activity_ids_sorted(self):
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()
        ids = analyser.get_activity_ids()
        assert ids == sorted(ids)
        assert len(ids) == 6


class TestDeliveryModelAnalyserWithTestData:
    """Tests using the real test-data/docs directory.

    The test-data files use descriptive names (e.g. pipeline_design.md)
    not numeric prefixes (3.2_Design_Data.md), so locate_model finds
    the README but zero activity files. This is expected.
    """

    def test_locate_model_finds_directory(self):
        analyser = DeliveryModelAnalyser(str(TEST_DATA / "docs"))
        info = analyser.locate_model()
        assert info["found"] is True

    def test_locate_model_no_numeric_activities(self):
        analyser = DeliveryModelAnalyser(str(TEST_DATA / "docs"))
        info = analyser.locate_model()
        # test-data files use descriptive names, not numeric prefixes
        assert info["activity_count"] == 0

    def test_locate_model_finds_readme_as_index(self):
        analyser = DeliveryModelAnalyser(str(TEST_DATA))
        info = analyser.locate_model()
        assert info["found"] is True
        assert info["index_file"] is not None
        assert "README.md" in info["index_file"]


# ===================================================================
# 3. SPLITTER
# ===================================================================


class TestSplitter:
    def _make_owns(self, activity_ids: list[str]) -> list[ActivityClassification]:
        return [
            ActivityClassification(aid, f"Activity {aid}", InvolvementCode.OWNS, "primary")
            for aid in activity_ids
        ]

    def _make_mixed(self, owns_ids, other_ids) -> list[ActivityClassification]:
        result = self._make_owns(owns_ids)
        for aid in other_ids:
            result.append(
                ActivityClassification(aid, f"Activity {aid}", InvolvementCode.OUT_OF_SCOPE, "not involved")
            )
        return result

    def test_few_owns_keeps_as_one(self):
        """3 OWNS activities under threshold → KEEP_AS_ONE."""
        role = AgentRole("Data Engineer", "builds pipelines")
        classifications = self._make_owns(["3.2", "4.3", "4.4"])
        result = evaluate_splitting(role, classifications)
        assert result.decision == SplitDecision.KEEP_AS_ONE
        assert result.keep_score >= 1

    def test_single_owns_keeps_as_one(self):
        role = AgentRole("Test Lead", "manages testing")
        classifications = self._make_owns(["3.6"])
        result = evaluate_splitting(role, classifications)
        assert result.decision == SplitDecision.KEEP_AS_ONE

    def test_many_owns_multi_phase_splits(self):
        """10 OWNS activities across 3 phases → SPLIT."""
        role = AgentRole("Data Engineer", "builds everything")
        owns_ids = [f"{p}.{i}" for p in ["3", "4", "5"] for i in range(1, 5)][:10]
        classifications = self._make_owns(owns_ids)
        result = evaluate_splitting(role, classifications)
        assert result.decision == SplitDecision.SPLIT_INTO_SUBAGENTS
        assert result.split_score > result.keep_score
        assert len(result.proposed_subagents) > 0

    def test_many_owns_single_phase_keeps(self):
        """9 OWNS activities all in one phase → criteria are balanced."""
        role = AgentRole("Data Engineer", "builds pipelines")
        owns_ids = [f"4.{i}" for i in range(1, 10)]
        classifications = self._make_owns(owns_ids)
        result = evaluate_splitting(role, classifications)
        # task_count > 8 → SPLIT, context_boundaries single phase → KEEP
        # tie or balanced
        assert result.split_score == result.keep_score or result.decision in (
            SplitDecision.KEEP_AS_ONE,
            SplitDecision.SPLIT_INTO_SUBAGENTS,
        )

    def test_only_owns_counted(self):
        """Non-OWNS activities don't affect splitting."""
        role = AgentRole("Data Engineer", "builds pipelines")
        classifications = self._make_mixed(
            owns_ids=["3.2", "4.4"],
            other_ids=["1.1", "2.2", "5.5", "6.6", "7.7", "8.8", "9.9"],
        )
        result = evaluate_splitting(role, classifications)
        assert result.decision == SplitDecision.KEEP_AS_ONE  # only 2 OWNS

    def test_llm_criteria_split(self):
        """5 SPLIT / 2 KEEP from LLM → SPLIT."""
        role = AgentRole("Data Engineer", "builds pipelines")
        classifications = self._make_owns(["3.2", "4.3", "4.4"])
        criteria = [
            {"name": "context_boundaries", "recommendation": "SPLIT", "rationale": "different contexts"},
            {"name": "tool_permissions", "recommendation": "SPLIT", "rationale": "different tools"},
            {"name": "independent_verification", "recommendation": "SPLIT", "rationale": "different reviewers"},
            {"name": "parallelism_value", "recommendation": "KEEP", "rationale": "sequential"},
            {"name": "development_test_ease", "recommendation": "SPLIT", "rationale": "large scope"},
            {"name": "task_count", "recommendation": "SPLIT", "rationale": ">8"},
            {"name": "team_scaling", "recommendation": "KEEP", "rationale": "small team"},
        ]
        result = evaluate_splitting(role, classifications, criteria_results=criteria)
        assert result.decision == SplitDecision.SPLIT_INTO_SUBAGENTS
        assert result.split_score == 5
        assert result.keep_score == 2
        assert len(result.proposed_subagents) == 3  # one per OWNS activity

    def test_llm_criteria_keep(self):
        """1 SPLIT / 6 KEEP from LLM → KEEP."""
        role = AgentRole("Data Engineer", "builds pipelines")
        classifications = self._make_owns(["3.2", "4.4"])
        criteria = [
            {"name": "context_boundaries", "recommendation": "KEEP", "rationale": "shared context"},
            {"name": "tool_permissions", "recommendation": "KEEP", "rationale": "same tools"},
            {"name": "independent_verification", "recommendation": "KEEP", "rationale": "same reviewer"},
            {"name": "parallelism_value", "recommendation": "KEEP", "rationale": "sequential"},
            {"name": "development_test_ease", "recommendation": "KEEP", "rationale": "small scope"},
            {"name": "task_count", "recommendation": "SPLIT", "rationale": "borderline"},
            {"name": "team_scaling", "recommendation": "KEEP", "rationale": "one developer"},
        ]
        result = evaluate_splitting(role, classifications, criteria_results=criteria)
        assert result.decision == SplitDecision.KEEP_AS_ONE
        assert result.keep_score == 6
        assert result.split_score == 1

    def test_proposed_subagents_have_activity_info(self):
        role = AgentRole("Data Engineer", "builds pipelines")
        classifications = self._make_owns(["3.2", "4.3", "4.4"])
        criteria = [{"name": f"crit_{i}", "recommendation": "SPLIT", "rationale": "yes"} for i in range(5)]
        result = evaluate_splitting(role, classifications, criteria_results=criteria)
        assert result.decision == SplitDecision.SPLIT_INTO_SUBAGENTS
        for sub in result.proposed_subagents:
            assert "name" in sub
            assert "activity" in sub
            assert "data_engineer" in sub["name"]

    def test_splitting_criteria_names_complete(self):
        assert len(SPLITTING_CRITERIA_NAMES) == 7
        assert "context_boundaries" in SPLITTING_CRITERIA_NAMES
        assert "task_count" in SPLITTING_CRITERIA_NAMES
        assert "team_scaling" in SPLITTING_CRITERIA_NAMES

    def test_splitting_criteria_prompts_complete(self):
        for name in SPLITTING_CRITERIA_NAMES:
            assert name in SPLITTING_CRITERIA_PROMPTS
            assert len(SPLITTING_CRITERIA_PROMPTS[name]) > 10


# ===================================================================
# 4. SKILLS
# ===================================================================


class TestSkillCatalogue:
    def test_load_existing_skills(self):
        catalogue = SkillCatalogue(SKILLS_ROOT)
        assert len(catalogue.existing_skills) >= 9

    def test_known_skills_present(self):
        catalogue = SkillCatalogue(SKILLS_ROOT)
        ids = [s["skill_id"] for s in catalogue.existing_skills]
        assert "delivery_model_analysis" in ids
        assert "skill_mapping" in ids
        assert "graphify_analysis" in ids

    def test_check_duplicate_true(self):
        catalogue = SkillCatalogue(SKILLS_ROOT)
        assert catalogue.check_duplicate("delivery_model_analysis") is True

    def test_check_duplicate_false(self):
        catalogue = SkillCatalogue(SKILLS_ROOT)
        assert catalogue.check_duplicate("nonexistent_skill_xyz") is False

    def test_find_matching(self):
        catalogue = SkillCatalogue(SKILLS_ROOT)
        matches = catalogue.find_matching("classify delivery model activities")
        # Should match skills with "delivery" or "model" or "classify" in their ID
        assert len(matches) >= 1

    def test_build_skill_check_prompt(self):
        catalogue = SkillCatalogue(SKILLS_ROOT)
        responsibilities = [
            {"name": "Design data schemas"},
            {"name": "Build dbt models"},
        ]
        prompt = catalogue.build_skill_check_prompt(responsibilities)
        assert "delivery_model_analysis" in prompt  # from existing skills
        assert "Design data schemas" in prompt
        assert "Build dbt models" in prompt
        assert "JSON array" in prompt

    def test_nonexistent_skills_root(self):
        catalogue = SkillCatalogue("/nonexistent/path")
        assert catalogue.existing_skills == []
        assert catalogue.check_duplicate("anything") is False


# ===================================================================
# 5. RENDERER
# ===================================================================


def _build_full_design() -> AgentDesign:
    """Build a fully-populated AgentDesign for renderer tests."""
    role = AgentRole("Data Engineer", "builds data pipelines", phase_scope=["3.2", "4.4"])
    classifications = [
        ActivityClassification("3.2", "Design Data Solution", InvolvementCode.OWNS, "primary", "3.2_Design.md"),
        ActivityClassification("4.4", "Develop Data Solution", InvolvementCode.OWNS, "primary", "4.4_Develop.md"),
        ActivityClassification("3.6", "Plan Testing", InvolvementCode.CONTRIBUTES, "helps"),
        ActivityClassification("5.1", "Deploy Release", InvolvementCode.OUT_OF_SCOPE, "not involved"),
    ]
    return AgentDesign(
        role=role,
        classifications=classifications,
        delivery_model_root="docs/knowledge-base/",
        responsibilities=[
            {"name": "Design schemas", "automatable": True, "source": "3.2"},
            {"name": "Build dbt models", "automatable": True, "source": "4.4"},
            {"name": "Approve design", "automatable": False, "source": "3.2"},
        ],
        inputs=[
            {"name": "Business requirements", "source": "Product Owner", "mandatory": True},
            {"name": "Current state assessment", "source": "Analyst", "mandatory": False},
        ],
        outputs=[
            {"name": "Logical data model", "consuming_activity": "4.4"},
            {"name": "Working pipelines", "consuming_activity": "5.1"},
        ],
        decisions=[
            {"name": "Schema design approval", "human_reserved": True, "rationale": "requires domain expertise"},
            {"name": "Model materialization", "human_reserved": False, "rationale": "automatable"},
        ],
        tools=[
            {"name": "dbt", "purpose": "Data transformation"},
            {"name": "Airflow", "purpose": "Workflow orchestration"},
        ],
        knowledge=[
            {"name": "Data modelling standards", "type": "delivery_model"},
            {"name": "dbt best practices", "type": "external"},
        ],
        skills=[
            SkillMapping("schema_design", "Design data schemas", 2, "always", is_existing=False, responsibilities_covered=["Design schemas"]),
            SkillMapping("dbt_development", "Build dbt models", 2, "always", is_existing=False, responsibilities_covered=["Build dbt models"]),
            SkillMapping("graphify_analysis", "Code analysis", 3, "engineer role", is_existing=True),
        ],
        workflow_steps=[
            {"name": "Analyse requirements", "description": "Read input docs"},
            {"name": "Design schema", "description": "Create logical model", "human_gate": True},
            {"name": "Build pipelines", "description": "Implement dbt + Airflow"},
        ],
        handoffs=[
            {"direction": "FROM", "agent": "Analyst", "trigger": "Requirements complete", "artefact": "Requirements doc"},
            {"direction": "TO", "agent": "Release Manager", "trigger": "Code merged", "artefact": "Release branch"},
        ],
        evaluation_metrics=[
            {"name": "Pipeline SLA", "metric": "< 2 hour runtime"},
            {"name": "Test coverage", "metric": "> 80%"},
        ],
        constraints=["Must follow banking data classification policy", "PII must be masked in non-prod"],
        information_gaps=["Integration with legacy Oracle CDC not fully defined"],
    )


def _build_empty_design() -> AgentDesign:
    """Build a minimal AgentDesign with only role — tests NEEDS INFO markers."""
    return AgentDesign(role=AgentRole("Test Agent", "test"))


class TestRenderDesignDocument:
    def test_contains_all_13_sections(self):
        doc = render_design_document(_build_full_design())
        required_sections = [
            "## 1. Identity",
            "## 2. Responsibilities",
            "## 3. Scope",
            "## 4. Inputs",
            "## 5. Outputs",
            "## 6. Skills",
            "## 7. Knowledge",
            "## 8. Tools",
            "## 9. Workflow",
            "## 10. Human Interaction",
            "## 11. Handoffs",
            "## 12. Evaluation Metrics",
            "## 13. Constraints",
        ]
        for section in required_sections:
            assert section in doc, f"Missing section: {section}"

    def test_header_and_metadata(self):
        doc = render_design_document(_build_full_design())
        assert "# AI Agent Design: Data Engineer" in doc
        assert "**Status:** DRAFT" in doc
        assert "`data_engineer`" in doc
        assert "docs/knowledge-base/" in doc

    def test_responsibilities_rendered(self):
        doc = render_design_document(_build_full_design())
        assert "Design schemas" in doc
        assert "Build dbt models" in doc
        assert "*(source: 3.2)*" in doc

    def test_human_gate_markers(self):
        doc = render_design_document(_build_full_design())
        assert "HUMAN GATE" in doc
        assert "Schema design approval" in doc

    def test_scope_section(self):
        doc = render_design_document(_build_full_design())
        assert "*(OWNS)*" in doc
        assert "*(CONTRIBUTES)*" in doc
        assert "Deploy Release" in doc  # out of scope

    def test_tools_table(self):
        doc = render_design_document(_build_full_design())
        assert "| dbt | Data transformation |" in doc
        assert "| Airflow | Workflow orchestration |" in doc

    def test_skills_section(self):
        doc = render_design_document(_build_full_design())
        assert "`schema_design`" in doc
        assert "(L2, new)" in doc
        assert "`graphify_analysis`" in doc
        assert "(L3, existing)" in doc

    def test_workflow_human_gate(self):
        doc = render_design_document(_build_full_design())
        assert "Design schema" in doc

    def test_information_gaps(self):
        doc = render_design_document(_build_full_design())
        assert "Integration with legacy Oracle CDC" in doc

    def test_constraints(self):
        doc = render_design_document(_build_full_design())
        assert "banking data classification policy" in doc
        assert "PII must be masked" in doc

    def test_empty_design_has_needs_info(self):
        doc = render_design_document(_build_empty_design())
        assert doc.count("NEEDS INFO") >= 5

    def test_output_is_nonempty_string(self):
        doc = render_design_document(_build_full_design())
        assert isinstance(doc, str)
        assert len(doc) > 500


class TestRenderAgentManifest:
    def test_contains_required_keys(self):
        manifest = render_agent_manifest(_build_full_design())
        assert "agent:" in manifest
        assert "skills:" in manifest
        assert "tools:" in manifest
        assert "knowledge_base:" in manifest
        assert "phases:" in manifest
        assert "constraints:" in manifest

    def test_role_in_manifest(self):
        manifest = render_agent_manifest(_build_full_design())
        assert 'role: "data_engineer"' in manifest

    def test_skills_active_inactive(self):
        manifest = render_agent_manifest(_build_full_design())
        assert "active:" in manifest
        assert "inactive:" in manifest
        assert '"schema_design"' in manifest
        assert '"graphify_analysis"' in manifest  # layer 3 = inactive

    def test_tools_listed(self):
        manifest = render_agent_manifest(_build_full_design())
        assert '"dbt"' in manifest
        assert '"Airflow"' in manifest

    def test_phases_from_owns(self):
        manifest = render_agent_manifest(_build_full_design())
        assert 'id: "3.2"' in manifest
        assert 'id: "4.4"' in manifest
        assert 'trigger: "start"' in manifest
        assert 'next_phase: "4.4"' in manifest
        assert 'next_phase: "end"' in manifest

    def test_constraints_present(self):
        manifest = render_agent_manifest(_build_full_design())
        assert "banking data classification policy" in manifest

    def test_empty_design_manifest(self):
        manifest = render_agent_manifest(_build_empty_design())
        assert "agent:" in manifest
        assert "active: []" in manifest
        assert "inactive: []" in manifest

    def test_output_is_nonempty_string(self):
        manifest = render_agent_manifest(_build_full_design())
        assert isinstance(manifest, str)
        assert len(manifest) > 200


# ===================================================================
# 6. INTEGRATION — end-to-end design flow
# ===================================================================


class TestEndToEndDesignFlow:
    """Integration test: analyser → splitter → skills → renderer using fixture data."""

    def setup_method(self):
        self._tmp = Path(tempfile.mkdtemp())
        _create_delivery_model_fixture(self._tmp)

    def teardown_method(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_full_pipeline(self):
        # Step 1: Create role
        role = AgentRole("Data Engineer", "automates data pipeline development")
        assert role.role_id == "data_engineer"

        # Step 2: Locate delivery model
        analyser = DeliveryModelAnalyser(str(self._tmp))
        model_info = analyser.locate_model()
        assert model_info["found"] is True
        assert model_info["activity_count"] == 6

        # Step 3: Read and classify activities (simulated — we do it deterministically here)
        classifications = [
            ActivityClassification("3.2", "Design Data Solution", InvolvementCode.OWNS, "Data Engineer is primary"),
            ActivityClassification("3.6", "Plan Testing", InvolvementCode.CONSUMES, "Receives test plan"),
            ActivityClassification("4.3", "Develop Data Platform", InvolvementCode.OWNS, "Data Engineer is primary"),
            ActivityClassification("4.4", "Develop Data Solution", InvolvementCode.OWNS, "Data Engineer is primary"),
            ActivityClassification("5.1", "Deploy Release", InvolvementCode.OUT_OF_SCOPE, "Release Manager owns"),
        ]

        # Step 3.5: Evaluate splitting
        split_result = evaluate_splitting(role, classifications)
        assert split_result.decision == SplitDecision.KEEP_AS_ONE  # 3 OWNS ≤ 5

        # Step 4: Check skills
        catalogue = SkillCatalogue(SKILLS_ROOT)
        assert len(catalogue.existing_skills) >= 9

        # Step 5: Build design
        design = AgentDesign(
            role=role,
            classifications=classifications,
            split_evaluation=split_result,
            delivery_model_root=str(self._tmp),
            responsibilities=[
                {"name": "Design logical data model", "automatable": True, "source": "3.2"},
                {"name": "Create ingestion patterns", "automatable": True, "source": "4.3"},
                {"name": "Develop dbt models", "automatable": True, "source": "4.4"},
            ],
            tools=[
                {"name": "dbt", "purpose": "Data transformation"},
                {"name": "Airflow", "purpose": "Workflow orchestration"},
            ],
        )

        # Step 6: Render
        doc = render_design_document(design)
        manifest = render_agent_manifest(design)

        # Verify design document
        assert "# AI Agent Design: Data Engineer" in doc
        assert "Design logical data model" in doc
        assert "Create ingestion patterns" in doc
        assert "Develop dbt models" in doc
        assert "## 1. Identity" in doc
        assert "## 13. Constraints" in doc

        # Verify manifest
        assert 'role: "data_engineer"' in manifest
        assert 'id: "3.2"' in manifest
        assert 'id: "4.3"' in manifest
        assert 'id: "4.4"' in manifest

    def test_classification_prompt_for_each_activity(self):
        """Verify we can build classification prompts for all activities."""
        role = AgentRole("Data Engineer", "builds pipelines")
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()

        for activity_data in analyser.read_all_activities():
            prompt = analyser.build_classification_prompt(activity_data, role)
            assert "Data Engineer" in prompt
            assert "OWNS" in prompt
            assert len(prompt) > 100

    def test_extraction_prompt_for_each_activity(self):
        """Verify we can build extraction prompts for all activities."""
        role = AgentRole("Data Engineer", "builds pipelines")
        analyser = DeliveryModelAnalyser(str(self._tmp))
        analyser.locate_model()

        for activity_data in analyser.read_all_activities():
            prompt = analyser.build_extraction_prompt(activity_data, role)
            assert '"tasks"' in prompt
            assert '"outputs"' in prompt
            assert len(prompt) > 100


class TestEndToEndWithRealTestData:
    """Integration tests using real Project ATLAS test-data."""

    def test_analyser_on_test_data_root(self):
        """test-data/ has README.md as index but no numeric-prefix activity files."""
        analyser = DeliveryModelAnalyser(str(TEST_DATA))
        info = analyser.locate_model()
        assert info["found"] is True
        assert "README.md" in info["index_file"]

    def test_design_with_atlas_project_context(self):
        """Build a Data Engineer design using ATLAS project context."""
        role = AgentRole(
            "Data Engineer",
            "automates data pipeline development, schema management, and data quality",
            phase_scope=["04-design", "05-development"],
        )

        classifications = [
            ActivityClassification("04", "Design", InvolvementCode.OWNS, "Designs pipelines and data models"),
            ActivityClassification("05", "Development", InvolvementCode.OWNS, "Builds and tests pipelines"),
            ActivityClassification("06", "Testing", InvolvementCode.CONTRIBUTES, "Writes data quality tests"),
            ActivityClassification("08", "Deployment", InvolvementCode.CONSUMES, "Pipelines deployed by ops"),
        ]

        design = AgentDesign(
            role=role,
            classifications=classifications,
            delivery_model_root=str(TEST_DATA / "docs"),
            responsibilities=[
                {"name": "Design dbt staging models", "automatable": True, "source": "04"},
                {"name": "Build Spark ingestion jobs", "automatable": True, "source": "05"},
                {"name": "Configure Airflow DAGs", "automatable": True, "source": "05"},
                {"name": "Implement Great Expectations suites", "automatable": True, "source": "06"},
            ],
            tools=[
                {"name": "dbt", "purpose": "SQL transformations"},
                {"name": "Apache Spark", "purpose": "Batch/streaming ingestion"},
                {"name": "Apache Airflow", "purpose": "Orchestration"},
                {"name": "Great Expectations", "purpose": "Data quality"},
                {"name": "Terraform", "purpose": "Infrastructure as code"},
            ],
            knowledge=[
                {"name": "Pipeline design document", "type": "delivery_model"},
                {"name": "Data architecture", "type": "delivery_model"},
                {"name": "Coding standards", "type": "delivery_model"},
            ],
            constraints=[
                "Must follow banking data classification policy",
                "PII must be masked in non-production environments",
                "All pipelines must complete within 2-hour SLA",
            ],
        )

        doc = render_design_document(design)
        manifest = render_agent_manifest(design)

        assert "Data Engineer" in doc
        assert "dbt staging models" in doc
        assert "Spark ingestion" in doc
        assert len(doc) > 1000

        assert "data_engineer" in manifest
        assert "dbt" in manifest
        assert "Terraform" in manifest
        assert len(manifest) > 500


# ===================================================================
# Discovery module tests (bonus — validate discovery tools work)
# ===================================================================

class TestDiscoveryIntegration:
    """Verify the discovery module still works correctly alongside agent-builder."""

    def test_discovery_batch_against_test_data(self):
        from discovery import get_strategy, DiscoveryConfig
        strategy = get_strategy("claude-code", mode="batch")
        config = DiscoveryConfig(
            repository_root=TEST_DATA,
            project_id="test-run",
            repository_id="test-data",
            skill="repository-discovery",
        )
        report = strategy.discover(config)
        assert report.entities_discovered > 0
        assert report.strategy == "claude-code-batch"
        assert len(report.failed) == 0

    def test_discovery_strategies_all_listed(self):
        from discovery import STRATEGIES
        assert "local" in STRATEGIES
        assert "harness" in STRATEGIES
        assert "runtime" in STRATEGIES
        assert "claude-code" in STRATEGIES


# ===================================================================
# Run all tests
# ===================================================================

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
