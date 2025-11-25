"""
neuromem - Standalone Memory Management Engine

A flexible memory management system for RAG applications with support for
vector databases, key-value stores, and graph structures.
"""

from .memory_collection import (
    BaseMemoryCollection,
    GraphMemoryCollection,
    KVMemoryCollection,
    VDBMemoryCollection,
)
from .memory_manager import MemoryManager

__version__ = "0.1.0"
__all__ = [
    "MemoryManager",
    "BaseMemoryCollection",
    "VDBMemoryCollection",
    "KVMemoryCollection",
    "GraphMemoryCollection",
]
