"""
PostInsert Action Module
========================

This module provides action strategies for post-insert memory processing.

Strategy Types:
- conflict_resolution: LLM CRUD (Mem0, MemGPT)
- decay_eviction: Forgetting Curve (MemoryBank)
- structure_enrichment: Link Evolution, Graph Construction, Heat Migration (A-Mem, HippoRAG, MemoryOS)
"""

from .base import BasePostInsertAction, PostInsertInput, PostInsertOutput

# Strategy-based imports
from .conflict_resolution import LLMCRUDAction, SemanticConsolidationAction
from .decay_eviction import ForgettingCurveAction, TimeDecayAction
from .none_action import NoneAction
from .operator import PostInsert
from .registry import PostInsertActionRegistry, get_action
from .structure_enrichment import GraphConstructionAction, HeatMigrationAction, LinkEvolutionAction

__all__ = [
    # Core
    "PostInsert",
    "BasePostInsertAction",
    "PostInsertInput",
    "PostInsertOutput",
    "PostInsertActionRegistry",
    "get_action",
    "NoneAction",
    # Conflict Resolution
    "LLMCRUDAction",
    "SemanticConsolidationAction",
    # Decay Eviction
    "ForgettingCurveAction",
    "TimeDecayAction",
    # Structure Enrichment
    "LinkEvolutionAction",
    "GraphConstructionAction",
    "HeatMigrationAction",
]
