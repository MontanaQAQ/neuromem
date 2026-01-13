"""
Structure Enrichment Strategies
===============================

Papers: A-Mem, HippoRAG
Strategy Type: structure_enrichment
Trigger Mechanism: retrieval (KNN-based) + semantic (LLM-based)

Enriches memory structure through:
- Link evolution (A-Mem auto-link)
- Graph construction (HippoRAG knowledge graph)
"""

from .graph_construction import GraphConstructionAction
from .link_evolution import LinkEvolutionAction

__all__ = ["LinkEvolutionAction", "GraphConstructionAction"]
