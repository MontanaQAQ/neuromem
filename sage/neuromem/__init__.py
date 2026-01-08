"""
neuromem - Standalone Memory Management Engine

A flexible memory management system for RAG applications with support for
vector databases, key-value stores, and graph structures.
"""

from ._version import __author__, __email__, __version__
from .memory_collection import UnifiedCollection
from .memory_manager import MemoryManager

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "MemoryManager",
    "UnifiedCollection",
]
