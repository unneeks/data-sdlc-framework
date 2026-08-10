"""
Metamodel definitions for Technical Twin entities.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DataAsset(BaseModel):
    id: str
    name: str
    asset_type: str  # e.g., "table", "view", "lakehouse_storage", "pubsub_topic"
    platform: str    # e.g., "BigQuery", "BigLake", "PubSub", "GCS"
    schema_name: str
    columns: List[Dict[str, str]] = Field(default_factory=list)
    owner: str = "Data Engineering Team"
    criticality: str = "HIGH"  # HIGH, MEDIUM, LOW
    status: str = "ACTIVE"     # ACTIVE, MIGRATING, DEPRECATED

class Pipeline(BaseModel):
    id: str
    name: str
    pipeline_type: str  # e.g., "dbt", "Dataflow", "Airflow", "Spark"
    repository_id: str
    inputs: List[str] = Field(default_factory=list)   # DataAsset IDs
    outputs: List[str] = Field(default_factory=list)  # DataAsset IDs
    status: str = "ACTIVE"

class LineageNode(BaseModel):
    id: str
    name: str
    node_type: str
    platform: str
    status: str = "STABLE"  # STABLE, CHANGED, REDIRECTED, IMPACTED, RISK

class LineageEdge(BaseModel):
    source: str
    target: str
    relationship_type: str = "DEPENDS_ON"
    provenance: Dict[str, Any] = Field(default_factory=lambda: {
        "confidence": 0.95,
        "source": "automated_scan",
        "verification_status": "CERTIFIED"
    })

class CodeArtifact(BaseModel):
    id: str
    file_path: str
    repository_id: str
    language: str  # "sql", "python", "yaml", "hcl"
    content_hash: str
    last_modified: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class InfrastructureResource(BaseModel):
    id: str
    resource_type: str  # e.g., "google_storage_bucket", "google_biglake_table"
    provider: str       # "gcp", "aws"
    config_file: str

class Test(BaseModel):
    id: str
    name: str
    test_type: str  # "schema_parity", "reconciliation", "data_quality", "downstream_regression"
    target_asset: str
    status: str = "PASSED"  # PASSED, FAILED, SKIPPED
    metrics: Dict[str, Any] = Field(default_factory=dict)

class Change(BaseModel):
    id: str
    title: str
    description: str
    change_type: str  # e.g., "ARCHITECTURAL_MIGRATION", "SOURCE_SCHEMA_CHANGE"
    modified_files: List[str] = Field(default_factory=list)
    impacted_assets: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Project(BaseModel):
    id: str
    name: str
    description: str
    technology_stack: List[str] = Field(default_factory=list)
    data_assets_count: int = 100
    pipelines_count: int = 40
    active_plan_id: Optional[str] = None
