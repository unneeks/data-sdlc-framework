"""Agent Builder core — shared logic for all platforms."""

from agent_builder.core.models import AgentRole, ActivityClassification, SplitEvaluation, AgentDesign
from agent_builder.core.analyser import DeliveryModelAnalyser
from agent_builder.core.splitter import evaluate_splitting
from agent_builder.core.skills import SkillCatalogue
from agent_builder.core.renderer import render_design_document, render_agent_manifest

__all__ = [
    "AgentRole",
    "ActivityClassification",
    "SplitEvaluation",
    "AgentDesign",
    "DeliveryModelAnalyser",
    "evaluate_splitting",
    "SkillCatalogue",
    "render_design_document",
    "render_agent_manifest",
]
