"""
Tests for the discovery module — tools, strategies, registry, and end-to-end integration.

Uses the Project ATLAS test-data as fixtures:
  test-data/code/         — dbt models, spark jobs, airflow dags, governance configs
  test-data/docs/         — 28 markdown delivery docs (01-discovery → 10-transition-to-bau)
  test-data/infrastructure/ — terraform modules
  test-data/agent-demo-de/  — agentic data engineering reference code
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

TEST_DATA = root_dir / "test-data"


# ---------------------------------------------------------------------------
# 1. discovery.tools.walk
# ---------------------------------------------------------------------------

class TestWalkRepository:

    def test_walk_returns_candidates(self):
        from discovery.tools.walk import walk_repository
        result = walk_repository(str(TEST_DATA))
        assert result["total_candidates"] > 0
        assert len(result["technical"]) > 0
        assert len(result["delivery"]) > 0

    def test_walk_total_candidate_count(self):
        from discovery.tools.walk import walk_repository
        result = walk_repository(str(TEST_DATA))
        assert result["total_candidates"] == len(result["technical"]) + len(result["delivery"])

    def test_walk_sql_classified(self):
        from discovery.tools.walk import walk_repository
        result = walk_repository(str(TEST_DATA))
        sql_files = [c for c in result["technical"] if c["source_kind"] == "sql"]
        assert len(sql_files) >= 8  # 3 staging + 2 intermediate + 3 marts + migration
        sql_paths = {c["path"] for c in sql_files}
        assert any("stg_customer_accounts.sql" in p for p in sql_paths)
        assert any("mart_customer_360.sql" in p for p in sql_paths)

    def test_walk_python_dags_classified(self):
        from discovery.tools.walk import walk_repository
        result = walk_repository(str(TEST_DATA))
        python_files = [c for c in result["technical"] if c["source_kind"] == "python"]
        python_paths = {c["path"] for c in python_files}
        assert any("daily_dbt_dag.py" in p for p in python_paths)
        assert any("daily_ingestion_dag.py" in p for p in python_paths)

    def test_walk_terraform_classified(self):
        from discovery.tools.walk import walk_repository
        result = walk_repository(str(TEST_DATA))
        tf_files = [c for c in result["technical"] if c["source_kind"] == "terraform"]
        assert len(tf_files) >= 4  # main.tf + multiple modules
        tf_paths = {c["path"] for c in tf_files}
        assert any("infrastructure/terraform/main.tf" in p for p in tf_paths)

    def test_walk_markdown_delivery(self):
        from discovery.tools.walk import walk_repository
        result = walk_repository(str(TEST_DATA))
        md_files = result["delivery"]
        assert all(c["source_kind"] == "markdown" for c in md_files)
        md_paths = {c["path"] for c in md_files}
        assert any("pipeline_design.md" in p for p in md_paths)
        assert any("test_strategy.md" in p for p in md_paths)
        assert any("acceptance_criteria.md" in p for p in md_paths)

    def test_walk_extra_exclude_dirs(self):
        from discovery.tools.walk import walk_repository
        full = walk_repository(str(TEST_DATA))
        filtered = walk_repository(str(TEST_DATA), extra_exclude_dirs=["agent-demo-de"])
        assert filtered["total_candidates"] < full["total_candidates"]
        for c in filtered["technical"] + filtered["delivery"]:
            assert "agent-demo-de" not in c["path"]

    def test_walk_by_source_kind_dict(self):
        from discovery.tools.walk import walk_repository
        result = walk_repository(str(TEST_DATA))
        bsk = result["by_source_kind"]
        assert "sql" in bsk
        assert "terraform" in bsk
        assert "markdown" in bsk
        total_from_bsk = sum(bsk.values())
        assert total_from_bsk == result["total_candidates"]


class TestClassifyFile:

    def test_sql(self):
        from discovery.tools.walk import classify_file
        assert classify_file("models/staging/stg_customer.sql") == "sql"

    def test_python_dag(self):
        from discovery.tools.walk import classify_file
        assert classify_file("dags/daily_ingestion_dag.py") == "python"

    def test_python_spark(self):
        from discovery.tools.walk import classify_file
        assert classify_file("ingestion/spark_jobs/load_data.py") == "python"

    def test_terraform(self):
        from discovery.tools.walk import classify_file
        assert classify_file("infrastructure/main.tf") == "terraform"

    def test_dockerfile(self):
        from discovery.tools.walk import classify_file
        assert classify_file("app/Dockerfile") == "dockerfile"

    def test_compose(self):
        from discovery.tools.walk import classify_file
        assert classify_file("docker-compose.yml") == "compose"

    def test_ci_workflow(self):
        from discovery.tools.walk import classify_file
        assert classify_file(".github/workflows/ci.yml") == "ci_workflow"

    def test_markdown(self):
        from discovery.tools.walk import classify_file
        assert classify_file("docs/architecture.md") == "markdown"

    def test_dbt_project_yaml(self):
        from discovery.tools.walk import classify_file
        assert classify_file("transformation/dbt_project.yml") == "yaml_config"

    def test_soda_checks(self):
        from discovery.tools.walk import classify_file
        assert classify_file("quality/soda/checks/orders_checks.yml") == "yaml_config"

    def test_governance_json(self):
        from discovery.tools.walk import classify_file
        assert classify_file("governance/policies/classification.json") == "json_config"

    def test_unrecognised_returns_none(self):
        from discovery.tools.walk import classify_file
        assert classify_file("random/file.txt") is None
        assert classify_file("lib/utils.py") is None  # no dag/spark/ingestion keyword
        assert classify_file("images/logo.png") is None

    def test_entity_types_mapping(self):
        from discovery.tools.walk import SOURCE_KIND_ENTITY_TYPES
        assert "Pipeline" in SOURCE_KIND_ENTITY_TYPES["sql"]
        assert "Infrastructure" in SOURCE_KIND_ENTITY_TYPES["terraform"]
        assert "DeliveryArtifact" in SOURCE_KIND_ENTITY_TYPES["markdown"]


# ---------------------------------------------------------------------------
# 2. discovery.tools.read
# ---------------------------------------------------------------------------

class TestReadFile:

    def test_read_sql_file(self):
        from discovery.tools.read import read_file
        result = read_file(str(TEST_DATA), "code/transformation/models/staging/stg_customer_accounts.sql")
        assert "error" not in result
        assert "content" in result
        assert "source('raw_banking'" in result["content"]
        assert result["size"] > 0
        assert result["lines"] > 0

    def test_read_markdown_file(self):
        from discovery.tools.read import read_file
        result = read_file(str(TEST_DATA), "docs/04-design/pipeline_design.md")
        assert "error" not in result
        assert "Pipeline Design" in result["content"]

    def test_read_nonexistent_file(self):
        from discovery.tools.read import read_file
        result = read_file(str(TEST_DATA), "does/not/exist.sql")
        assert result["error"] == "file_not_found"

    def test_read_directory_is_error(self):
        from discovery.tools.read import read_file
        result = read_file(str(TEST_DATA), "code")
        assert result["error"] == "not_a_file"

    def test_read_file_too_large(self):
        from discovery.tools.read import read_file, MAX_FILE_SIZE
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", dir=str(TEST_DATA),
                                         delete=False, prefix="large_") as f:
            f.write("x" * (MAX_FILE_SIZE + 1))
            temp_name = os.path.basename(f.name)
        try:
            result = read_file(str(TEST_DATA), temp_name)
            assert result["error"] == "file_too_large"
            assert result["size"] > MAX_FILE_SIZE
            assert "preview" in result
        finally:
            os.unlink(os.path.join(str(TEST_DATA), temp_name))


class TestReadFilesBatch:

    def test_batch_read(self):
        from discovery.tools.read import read_files_batch
        result = read_files_batch(str(TEST_DATA), [
            "code/transformation/models/staging/stg_customer_accounts.sql",
            "docs/04-design/pipeline_design.md",
            "does/not/exist.txt",
        ])
        assert result["requested"] == 3
        assert result["succeeded"] == 2
        assert "error" not in result["files"]["code/transformation/models/staging/stg_customer_accounts.sql"]
        assert "error" in result["files"]["does/not/exist.txt"]


# ---------------------------------------------------------------------------
# 3. discovery.tools.resolve
# ---------------------------------------------------------------------------

class TestResolveRelationships:

    def _make_entities(self):
        from discovery.result import DiscoveredEntity
        return [
            DiscoveredEntity("Pipeline", "pipeline:stg_customers", "stg_customers", "stg.sql",
                             attributes={"source_path": "models/staging/stg_customers.sql"}),
            DiscoveredEntity("Pipeline", "pipeline:mart_orders", "mart_orders", "mart.sql",
                             attributes={"source_path": "models/marts/mart_orders.sql"}),
            DiscoveredEntity("DataAsset", "dataasset:raw_customers", "raw_customers", "src.yml"),
        ]

    def test_build_entity_index_by_name(self):
        from discovery.tools.resolve import build_entity_index
        entities = self._make_entities()
        index = build_entity_index(entities)
        assert "stg_customers" in index
        assert "mart_orders" in index
        assert "raw_customers" in index

    def test_build_entity_index_by_entity_id(self):
        from discovery.tools.resolve import build_entity_index
        index = build_entity_index(self._make_entities())
        assert "pipeline:stg_customers" in index
        assert "dataasset:raw_customers" in index

    def test_build_entity_index_by_type_name(self):
        from discovery.tools.resolve import build_entity_index
        index = build_entity_index(self._make_entities())
        assert "pipeline:stg_customers" in index
        assert "dataasset:raw_customers" in index

    def test_build_entity_index_by_stem(self):
        from discovery.tools.resolve import build_entity_index
        index = build_entity_index(self._make_entities())
        assert "stg_customers" in index  # stem of source_path

    def test_resolve_valid_relationship(self):
        from discovery.tools.resolve import resolve_relationships
        entities = self._make_entities()
        candidates = [{
            "relationship_type": "DEPENDS_ON",
            "source": "mart_orders",
            "target": "stg_customers",
            "confidence": 1.0,
            "source_document": "mart.sql",
        }]
        result = resolve_relationships(candidates, entities)
        assert result["resolved"] == 1
        assert result["skipped"] == 0
        assert result["relationships"][0]["source_ref"] == "pipeline:mart_orders"
        assert result["relationships"][0]["target_ref"] == "pipeline:stg_customers"

    def test_resolve_unresolved_source(self):
        from discovery.tools.resolve import resolve_relationships
        entities = self._make_entities()
        candidates = [{
            "relationship_type": "DEPENDS_ON",
            "source": "nonexistent",
            "target": "stg_customers",
            "source_document": "x.sql",
        }]
        result = resolve_relationships(candidates, entities)
        assert result["resolved"] == 0
        assert result["skipped"] == 1
        assert "unresolved_source" in result["skipped_details"][0]["kind"]

    def test_resolve_unresolved_target(self):
        from discovery.tools.resolve import resolve_relationships
        entities = self._make_entities()
        candidates = [{
            "relationship_type": "DEPENDS_ON",
            "source": "mart_orders",
            "target": "nonexistent_table",
            "source_document": "x.sql",
        }]
        result = resolve_relationships(candidates, entities)
        assert result["resolved"] == 0
        assert result["skipped"] == 1
        assert "unresolved_target" in result["skipped_details"][0]["kind"]

    def test_resolve_multiple_mixed(self):
        from discovery.tools.resolve import resolve_relationships
        entities = self._make_entities()
        candidates = [
            {"relationship_type": "DEPENDS_ON", "source": "mart_orders", "target": "stg_customers",
             "source_document": "a.sql"},
            {"relationship_type": "DEPENDS_ON", "source": "mart_orders", "target": "raw_customers",
             "source_document": "a.sql"},
            {"relationship_type": "DEPENDS_ON", "source": "ghost", "target": "stg_customers",
             "source_document": "b.sql"},
        ]
        result = resolve_relationships(candidates, entities)
        assert result["total_candidates"] == 3
        assert result["resolved"] == 2
        assert result["skipped"] == 1


# ---------------------------------------------------------------------------
# 4. discovery.tools.ingest
# ---------------------------------------------------------------------------

class TestIngest:

    def setup_method(self):
        from discovery.tools.ingest import reset_graph
        reset_graph()

    def test_ingest_entities_basic(self):
        from discovery.tools.ingest import ingest_entities, get_graph_state
        result = ingest_entities("proj-1", [
            {"entity_type": "Pipeline", "name": "my_pipeline", "source_document": "dag.py"},
            {"entity_type": "DataAsset", "name": "my_table", "source_document": "schema.yml"},
        ])
        assert result["ingested"] == 2
        assert result["failed"] == 0
        assert result["by_type"]["Pipeline"] == 1
        assert result["by_type"]["DataAsset"] == 1

        state = get_graph_state("proj-1")
        assert state["entity_count"] == 2

    def test_ingest_entities_missing_fields(self):
        from discovery.tools.ingest import ingest_entities
        result = ingest_entities("proj-1", [
            {"entity_type": "Pipeline"},  # missing name
            {"name": "orphan"},  # missing entity_type
            {},  # both missing
        ])
        assert result["ingested"] == 0
        assert result["failed"] == 3
        assert all(f["kind"] == "missing_required_field" for f in result["failures"])

    def test_ingest_entities_idempotent(self):
        from discovery.tools.ingest import ingest_entities, get_graph_state
        entity = {"entity_type": "Pipeline", "name": "dup_pipeline", "entity_id": "pipeline:dup"}
        ingest_entities("proj-1", [entity])
        ingest_entities("proj-1", [entity])
        state = get_graph_state("proj-1")
        assert state["entity_count"] == 1  # not 2

    def test_ingest_generates_deterministic_id(self):
        from discovery.tools.ingest import ingest_entities, get_graph_state
        ingest_entities("proj-1", [
            {"entity_type": "Pipeline", "name": "My Complex/Pipeline.Name"},
        ])
        state = get_graph_state("proj-1")
        entity = state["entities"][0]
        assert entity["entity_id"] == "pipeline:my_complex_pipeline_name"

    def test_ingest_relationships_by_entity_id(self):
        from discovery.tools.ingest import ingest_entities, ingest_relationships
        ingest_entities("proj-1", [
            {"entity_type": "Pipeline", "name": "source_pipe", "entity_id": "pipeline:source"},
            {"entity_type": "DataAsset", "name": "target_asset", "entity_id": "dataasset:target"},
        ])
        result = ingest_relationships("proj-1", [{
            "relationship_type": "PRODUCES",
            "source_ref": "pipeline:source",
            "target_ref": "dataasset:target",
        }])
        assert result["ingested"] == 1
        assert result["failed"] == 0

    def test_ingest_relationships_by_name(self):
        from discovery.tools.ingest import ingest_entities, ingest_relationships
        ingest_entities("proj-1", [
            {"entity_type": "Pipeline", "name": "alpha_dag"},
            {"entity_type": "Pipeline", "name": "beta_dag"},
        ])
        result = ingest_relationships("proj-1", [{
            "relationship_type": "DEPENDS_ON",
            "source_ref": "alpha_dag",
            "target_ref": "beta_dag",
        }])
        assert result["ingested"] == 1
        assert result["failed"] == 0

    def test_ingest_relationships_dangling_source(self):
        from discovery.tools.ingest import ingest_entities, ingest_relationships
        ingest_entities("proj-1", [
            {"entity_type": "Pipeline", "name": "existing"},
        ])
        result = ingest_relationships("proj-1", [{
            "relationship_type": "DEPENDS_ON",
            "source_ref": "nonexistent",
            "target_ref": "existing",
        }])
        assert result["ingested"] == 0
        assert result["failed"] == 1
        assert result["failures"][0]["kind"] == "dangling_source"

    def test_ingest_relationships_dangling_target(self):
        from discovery.tools.ingest import ingest_entities, ingest_relationships
        ingest_entities("proj-1", [
            {"entity_type": "Pipeline", "name": "existing"},
        ])
        result = ingest_relationships("proj-1", [{
            "relationship_type": "DEPENDS_ON",
            "source_ref": "existing",
            "target_ref": "ghost",
        }])
        assert result["ingested"] == 0
        assert result["failed"] == 1
        assert result["failures"][0]["kind"] == "dangling_target"

    def test_ingest_relationships_missing_fields(self):
        from discovery.tools.ingest import ingest_entities, ingest_relationships
        ingest_entities("proj-1", [{"entity_type": "Pipeline", "name": "placeholder"}])
        result = ingest_relationships("proj-1", [
            {"relationship_type": "DEPENDS_ON"},  # missing source and target
        ])
        assert result["failed"] == 1
        assert result["failures"][0]["kind"] == "missing_required_field"

    def test_reset_graph(self):
        from discovery.tools.ingest import ingest_entities, reset_graph, get_graph_state
        ingest_entities("proj-1", [{"entity_type": "Pipeline", "name": "p1"}])
        reset_graph()
        state = get_graph_state()
        assert state["entity_count"] == 0
        assert state["relationship_count"] == 0

    def test_graph_state_project_filter(self):
        from discovery.tools.ingest import ingest_entities, get_graph_state
        ingest_entities("proj-a", [{"entity_type": "Pipeline", "name": "a1"}])
        ingest_entities("proj-b", [{"entity_type": "Pipeline", "name": "b1"}, {"entity_type": "Pipeline", "name": "b2"}])
        state_a = get_graph_state("proj-a")
        state_b = get_graph_state("proj-b")
        assert state_a["entity_count"] == 1
        assert state_b["entity_count"] == 2


# ---------------------------------------------------------------------------
# 5. discovery.registry
# ---------------------------------------------------------------------------

class TestRegistry:

    def test_list_strategies(self):
        from discovery.registry import list_strategies
        strategies = list_strategies()
        names = {s["name"] for s in strategies}
        assert names == {"local", "harness", "runtime", "claude-code"}

    def test_list_strategies_has_descriptions(self):
        from discovery.registry import list_strategies
        for s in list_strategies():
            assert "description" in s
            assert len(s["description"]) > 10

    def test_get_strategy_claude_code(self):
        from discovery.registry import get_strategy
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        strategy = get_strategy("claude-code", mode="batch")
        assert isinstance(strategy, ClaudeCodeStrategy)
        assert strategy.name == "claude-code"

    def test_get_strategy_local(self):
        """LocalStrategy requires a client, so just test instantiation fails cleanly."""
        from discovery.registry import get_strategy
        import pytest
        with pytest.raises(TypeError):
            get_strategy("local")  # missing required 'client' arg

    def test_get_strategy_unknown_raises(self):
        from discovery.registry import get_strategy
        import pytest
        with pytest.raises(ValueError, match="Unknown strategy 'nope'"):
            get_strategy("nope")

    def test_strategies_dict_has_all_four(self):
        from discovery.registry import STRATEGIES
        assert len(STRATEGIES) == 4
        assert "local" in STRATEGIES
        assert "harness" in STRATEGIES
        assert "runtime" in STRATEGIES
        assert "claude-code" in STRATEGIES


# ---------------------------------------------------------------------------
# 6. discovery.strategies.claude_code (batch mode against test-data)
# ---------------------------------------------------------------------------

class TestClaudeCodeStrategy:

    def setup_method(self):
        from discovery.tools.ingest import reset_graph
        reset_graph()

    def test_discover_returns_report(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        config = DiscoveryConfig(
            repository_root=TEST_DATA,
            project_id="test-cc",
            repository_id="atlas-test",
        )
        report = strategy.discover(config)
        assert report.project_id == "test-cc"
        assert report.strategy == "claude-code-batch"
        assert report.entities_discovered > 0

    def test_discover_finds_pipelines(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        config = DiscoveryConfig(repository_root=TEST_DATA, project_id="test-pipe")
        report = strategy.discover(config)
        assert "Pipeline" in report.entities_by_type
        assert report.entities_by_type["Pipeline"] >= 8  # dbt models + dags

    def test_discover_finds_data_assets(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        config = DiscoveryConfig(repository_root=TEST_DATA, project_id="test-da")
        report = strategy.discover(config)
        assert "DataAsset" in report.entities_by_type
        asset_names = {e.name for e in report.entities if e.entity_type == "DataAsset"}
        assert any("raw_banking" in n for n in asset_names)

    def test_discover_finds_infrastructure(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        config = DiscoveryConfig(repository_root=TEST_DATA, project_id="test-infra")
        report = strategy.discover(config)
        assert "Infrastructure" in report.entities_by_type
        infra_names = {e.name for e in report.entities if e.entity_type == "Infrastructure"}
        assert any("aws_" in n for n in infra_names)

    def test_discover_finds_delivery_artifacts(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        config = DiscoveryConfig(repository_root=TEST_DATA, project_id="test-del")
        report = strategy.discover(config)
        assert "DeliveryArtifact" in report.entities_by_type
        assert report.entities_by_type["DeliveryArtifact"] >= 10

    def test_discover_finds_gates(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        config = DiscoveryConfig(repository_root=TEST_DATA, project_id="test-gate")
        report = strategy.discover(config)
        assert "Gate" in report.entities_by_type
        assert report.entities_by_type["Gate"] >= 5

    def test_discover_dbt_lineage_relationships(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        config = DiscoveryConfig(repository_root=TEST_DATA, project_id="test-lin")
        report = strategy.discover(config)
        assert report.relationships_discovered > 0
        depends_on = [r for r in report.relationships if r.relationship_type == "DEPENDS_ON"]
        assert len(depends_on) >= 6
        source_refs = {r.source_ref for r in depends_on}
        target_refs = {r.target_ref for r in depends_on}
        assert any("mart_customer_360" in r for r in source_refs)
        assert any("stg_customer_accounts" in r for r in target_refs)

    def test_discover_no_failures(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        config = DiscoveryConfig(repository_root=TEST_DATA, project_id="test-nf")
        report = strategy.discover(config)
        assert len(report.failed) == 0

    def test_discover_with_exclude_dirs(self):
        from discovery.strategies.claude_code import ClaudeCodeStrategy
        from discovery.strategy import DiscoveryConfig
        strategy = ClaudeCodeStrategy(mode="batch")
        full = strategy.discover(DiscoveryConfig(
            repository_root=TEST_DATA, project_id="test-full",
        ))
        from discovery.tools.ingest import reset_graph
        reset_graph()
        filtered = strategy.discover(DiscoveryConfig(
            repository_root=TEST_DATA, project_id="test-filt",
            extra_exclude_dirs=frozenset(["agent-demo-de"]),
        ))
        assert filtered.entities_discovered < full.entities_discovered

    def test_skill_instructions_loadable(self):
        strategy = _make_cc_strategy()
        instructions = strategy.skill_instructions
        assert "Walk and Classify" in instructions
        assert "Technical Extraction" in instructions

    def test_name_property(self):
        strategy = _make_cc_strategy()
        assert strategy.name == "claude-code"


def _make_cc_strategy():
    from discovery.strategies.claude_code import ClaudeCodeStrategy
    return ClaudeCodeStrategy(mode="batch")


# ---------------------------------------------------------------------------
# 7. discovery.result — DiscoveryReport dataclass
# ---------------------------------------------------------------------------

class TestDiscoveryResult:

    def test_report_defaults(self):
        from discovery.result import DiscoveryReport
        r = DiscoveryReport(project_id="p", strategy="s", skill="sk")
        assert r.entities_discovered == 0
        assert r.relationships_discovered == 0
        assert r.entities == []
        assert r.skipped == []
        assert r.failed == []

    def test_report_summary(self):
        from discovery.result import DiscoveryReport
        r = DiscoveryReport(project_id="atlas", strategy="claude-code-batch",
                            skill="repository-discovery", entities_discovered=42,
                            relationships_discovered=10,
                            entities_by_type={"Pipeline": 20, "DataAsset": 22})
        s = r.summary()
        assert "atlas" in s
        assert "42" in s
        assert "Pipeline" in s

    def test_report_to_dict(self):
        from discovery.result import DiscoveryReport, DiscoverySkip, DiscoveryFailure
        r = DiscoveryReport(
            project_id="p", strategy="s", skill="sk",
            entities_discovered=5,
            skipped=[DiscoverySkip("too_large", "100KB", "big.sql")],
            failed=[DiscoveryFailure("parse_error", "bad json", "broken.json")],
        )
        d = r.to_dict()
        assert d["project_id"] == "p"
        assert len(d["skipped"]) == 1
        assert d["skipped"][0]["kind"] == "too_large"
        assert len(d["failed"]) == 1

    def test_discovered_entity_dataclass(self):
        from discovery.result import DiscoveredEntity
        e = DiscoveredEntity("Pipeline", "pipeline:test", "test", "test.sql")
        assert e.provenance == "INFERRED"
        assert e.confidence == 0.85
        assert e.attributes == {}

    def test_discovered_relationship_dataclass(self):
        from discovery.result import DiscoveredRelationship
        r = DiscoveredRelationship("DEPENDS_ON", "a", "b", 1.0, "src.sql")
        assert r.relationship_type == "DEPENDS_ON"
        assert r.source_ref == "a"
        assert r.target_ref == "b"


# ---------------------------------------------------------------------------
# 8. Integration — full pipeline end-to-end against test-data
# ---------------------------------------------------------------------------

class TestIntegration:

    def setup_method(self):
        from discovery.tools.ingest import reset_graph
        reset_graph()

    def test_full_pipeline_via_strategy(self):
        """End-to-end: walk → extract → resolve → ingest via claude-code batch."""
        from discovery import get_strategy, DiscoveryConfig
        from discovery.tools.ingest import get_graph_state

        strategy = get_strategy("claude-code", mode="batch")
        config = DiscoveryConfig(
            repository_root=TEST_DATA,
            project_id="integration-test",
            repository_id="atlas-integration",
        )
        report = strategy.discover(config)

        assert report.entities_discovered > 100
        assert report.relationships_discovered > 0
        assert len(report.failed) == 0
        assert "Pipeline" in report.entities_by_type
        assert "Infrastructure" in report.entities_by_type
        assert "DeliveryArtifact" in report.entities_by_type

        state = get_graph_state("integration-test")
        # entity_count may be slightly less than entities_discovered due to
        # duplicate entity_ids being deduplicated in the store
        assert state["entity_count"] >= report.entities_discovered - 10
        assert state["relationship_count"] == report.relationships_discovered

        entity_types = {e["entity_type"] for e in state["entities"]}
        assert entity_types >= {"Pipeline", "DataAsset", "Infrastructure", "DeliveryArtifact"}

    def test_full_pipeline_manual_steps(self):
        """Walk → read → extract → resolve → ingest step by step."""
        from discovery.tools.walk import walk_repository
        from discovery.tools.read import read_file
        from discovery.result import DiscoveredEntity
        from discovery.tools.resolve import resolve_relationships
        from discovery.tools.ingest import ingest_entities, ingest_relationships, get_graph_state

        # Step 1: Walk
        walk_result = walk_repository(str(TEST_DATA))
        assert walk_result["total_candidates"] > 50

        # Step 2: Read a few SQL files
        sql_files = [c for c in walk_result["technical"] if c["source_kind"] == "sql"]
        assert len(sql_files) >= 3
        staging_files = [f for f in sql_files if "staging" in f["path"]]

        # Step 3: Build entities from file paths
        entities = []
        rel_candidates = []
        for sf in staging_files:
            content_result = read_file(str(TEST_DATA), sf["path"])
            assert "error" not in content_result
            name = Path(sf["path"]).stem
            entities.append(DiscoveredEntity(
                entity_type="Pipeline",
                entity_id=f"pipeline:{name}",
                name=name,
                source_document=sf["path"],
                provenance="OBSERVED",
                confidence=1.0,
            ))

        # Add a mart that depends on staging
        entities.append(DiscoveredEntity(
            entity_type="Pipeline",
            entity_id="pipeline:mart_customer_360",
            name="mart_customer_360",
            source_document="models/marts/mart_customer_360.sql",
        ))
        rel_candidates.append({
            "relationship_type": "DEPENDS_ON",
            "source": "mart_customer_360",
            "target": "stg_customer_accounts",
            "source_document": "mart_customer_360.sql",
        })

        # Step 4: Resolve
        resolution = resolve_relationships(rel_candidates, entities)
        assert resolution["resolved"] == 1

        # Step 5: Ingest
        ingest_result = ingest_entities("manual-test", [
            {"entity_type": e.entity_type, "name": e.name, "entity_id": e.entity_id,
             "source_document": e.source_document}
            for e in entities
        ])
        assert ingest_result["ingested"] == len(entities)

        rel_result = ingest_relationships("manual-test", resolution["relationships"])
        assert rel_result["ingested"] == 1

        state = get_graph_state("manual-test")
        assert state["entity_count"] == len(entities)
        assert state["relationship_count"] == 1

    def test_dbt_lineage_preserved(self):
        """Verify the full dbt lineage from staging → intermediate → marts is resolved."""
        from discovery import get_strategy, DiscoveryConfig

        strategy = get_strategy("claude-code", mode="batch")
        config = DiscoveryConfig(
            repository_root=TEST_DATA / "code",
            project_id="dbt-lineage-test",
        )
        report = strategy.discover(config)

        depends_on = [r for r in report.relationships if r.relationship_type == "DEPENDS_ON"]
        source_targets = [(r.source_ref, r.target_ref) for r in depends_on]

        # stg → source
        assert any("stg_customer_accounts" in s and "raw_banking" in t for s, t in source_targets)
        # int → stg
        assert any("int_customer_enriched" in s and "stg_customer_accounts" in t for s, t in source_targets)
        # mart → int
        assert any("mart_customer_360" in s and "int_customer_enriched" in t for s, t in source_targets)
