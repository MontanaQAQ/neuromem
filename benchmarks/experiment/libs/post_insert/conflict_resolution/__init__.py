"""
Conflict Resolution Strategies
==============================

Papers: Mem0, Mem0ᵍ, TiM, MemGPT
Strategy Type: conflict_resolution
Trigger Mechanism: retrieval (similarity-based)

Handles memory conflicts through LLM-based CRUD decisions
and semantic consolidation (merge similar memories).
"""

from .llm_crud import LLMCRUDAction
from .semantic_consolidation import SemanticConsolidationAction

__all__ = ["LLMCRUDAction", "SemanticConsolidationAction"]
