"""
NeuroMem Search Engine module.

Provides various types of indexes for memory retrieval:
- VDB (Vector Database) indexes: FAISS, etc.
- KV (Key-Value) indexes: BM25, etc.
- Graph indexes: SimpleGraphIndex, etc.

Unified factory for all index types:
    from neuromem.search_engine import IndexFactory

    vdb_index = IndexFactory.create_vdb_index({"name": "my_vdb", "dim": 768})
    kv_index = IndexFactory.create_kv_index({"name": "my_kv"})
    graph_index = IndexFactory.create_graph_index({"name": "my_graph"})
"""

# Import base classes
from .graph_index import BaseGraphIndex, GraphIndexFactory, SimpleGraphIndex

# Import unified factory
from .index_factory import (
    IndexFactory,
    create_graph_index,
    create_kv_index,
    create_vdb_index,
)
from .kv_index import BaseKVIndex, BM25sIndex, KVIndexFactory
from .vdb_index import BaseVDBIndex, VDBIndexFactory

__all__ = [
    # Unified factory
    "IndexFactory",
    "create_vdb_index",
    "create_kv_index",
    "create_graph_index",
    # VDB
    "BaseVDBIndex",
    "VDBIndexFactory",
    # KV
    "BaseKVIndex",
    "BM25sIndex",
    "KVIndexFactory",
    # Graph
    "BaseGraphIndex",
    "SimpleGraphIndex",
    "GraphIndexFactory",
]
