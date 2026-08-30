"""Code analysers for deep repository walking.

Deterministic analysers rely on AST parsing, regex, and heuristics.
The ``llm_reasoning`` module adds optional LLM enrichment via AgentCore.
"""

from discovery.tools.analysers.module_analyser import analyse_modules
from discovery.tools.analysers.pattern_analyser import analyse_patterns
from discovery.tools.analysers.responsibility_analyser import analyse_responsibilities
from discovery.tools.analysers.sbom_analyser import analyse_sbom
from discovery.tools.analysers.llm_reasoning import run_reasoning_steps, enrich_deep_walk

__all__ = [
    "analyse_modules",
    "analyse_patterns",
    "analyse_responsibilities",
    "analyse_sbom",
    "enrich_deep_walk",
    "run_reasoning_steps",
]
