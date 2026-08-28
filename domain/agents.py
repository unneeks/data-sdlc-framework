"""
Domain entities for Agents, Skills, Tools, Knowledge Packs, Policies, and Delivery Contracts.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from domain.orchestration import AgentRuntimeKind

class Tool(BaseModel):
    id: str
    name: str
    description: str
    tool_type: str  # "cli", "api", "query", "scanner"
    parameters: Dict[str, Any] = Field(default_factory=dict)

class Skill(BaseModel):
    id: str
    name: str
    description: str
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"

class KnowledgePack(BaseModel):
    id: str
    name: str
    category: str
    documents_count: int

class Policy(BaseModel):
    id: str
    name: str
    policy_type: str  # "security", "data_quality", "governance", "release"
    rules: List[str] = Field(default_factory=list)

class Agent(BaseModel):
    id: str
    name: str
    version: str
    description: str
    engineering_role: str
    capabilities: List[str] = Field(default_factory=list)
    supported_delivery_types: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    knowledge_packs: List[str] = Field(default_factory=list)
    policies: List[str] = Field(default_factory=list)
    risk_level: str = "MEDIUM"
    autonomy_level: str = "SEMI_AUTOMATIC"  # AUTOMATIC, SEMI_AUTOMATIC, APPROVAL_REQUIRED
    trust_score: float = 0.94
    certification_status: str = "CERTIFIED"  # CERTIFIED, EVALUATING, DEPRECATED
    execution_kind: AgentRuntimeKind = AgentRuntimeKind.SERVER_RUN

class DeliveryContract(BaseModel):
    id: str
    task_id: str
    agent_id: str
    inputs: List[str]
    outputs: List[str]
    skills: List[str]
    tools: List[str]
    knowledge_packs: List[str]
    policies: List[str]
    approval_gate_id: str
    status: str = "ACTIVE"
