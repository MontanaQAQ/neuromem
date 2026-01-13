"""
Structure Enrichment Strategies
===============================

Papers: A-Mem, HippoRAG, MemoryOS
Strategy Type: structure_enrichment
Trigger Mechanism: retrieval (KNN-based) + semantic (LLM-based) + threshold (heat-based)

Enriches memory structure through:
- Link evolution (A-Mem auto-link)
- Graph construction (HippoRAG knowledge graph)
- Heat migration (MemoryOS tier-based migration)
"""

from .graph_construction import GraphConstructionAction
from .heat_migration import HeatMigrationAction
from .link_evolution import LinkEvolutionAction

__all__ = ["LinkEvolutionAction", "GraphConstructionAction", "HeatMigrationAction"]
