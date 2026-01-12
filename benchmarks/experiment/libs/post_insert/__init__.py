"""
PostInsert Action Module
========================

This module provides action strategies for post-insert memory processing.

Strategy Types:
- conflict_resolution: LLM CRUD, Semantic Consolidation (Mem0, Mem0ᵍ, TiM, MemGPT)
- decay_eviction: Forgetting Curve, Time Decay (MemoryBank, LD-Agent)
- structure_enrichment: Link Evolution, Graph Construction (A-Mem, HippoRAG)
- tier_migration: Heat Migration (MemoryOS)
"""

from .base import BasePostInsertAction, PostInsertInput, PostInsertOutput

# Strategy-based imports
from .conflict_resolution import LLMCRUDAction, SemanticConsolidationAction
from .decay_eviction import ForgettingCurveAction, TimeDecayAction
from .none_action import NoneAction
from .operator import PostInsert
from .registry import PostInsertActionRegistry, get_action
from .structure_enrichment import GraphConstructionAction, LinkEvolutionAction
from .tier_migration import HeatMigrationAction

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
    # Tier Migration
    "HeatMigrationAction",
]
