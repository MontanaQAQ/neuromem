"""
Unified Index Factory for NeuroMem.

Provides a single entry point for creating and loading all types of indexes:
- VDB (Vector Database) indexes: FAISS, etc.
- KV (Key-Value) indexes: BM25, etc.
- Graph indexes: SimpleGraphIndex, etc.

Example usage:
    from neuromem.search_engine import IndexFactory

    # Create VDB index
    vdb_index = IndexFactory.create_vdb_index({
        "name": "my_vdb",
        "dim": 768,
        "backend_type": "faiss",
    })

    # Create KV index
    kv_index = IndexFactory.create_kv_index({
        "name": "my_kv",
        "index_type": "bm25s",
    })

    # Create Graph index
    graph_index = IndexFactory.create_graph_index({
        "name": "my_graph",
        "index_type": "simple",
    })
"""

from typing import Any

from .graph_index import BaseGraphIndex, GraphIndexFactory, SimpleGraphIndex
from .kv_index import BaseKVIndex, BM25sIndex, KVIndexFactory
from .vdb_index import BaseVDBIndex, VDBIndexFactory


class IndexFactory:
    """
    Unified factory for creating all types of indexes.

    Provides a single entry point for index creation and management.
    Delegates to specialized factories for each index type.
    """

    # ============ VDB Index Registry ============

    _vdb_registry: dict[str, type[BaseVDBIndex]] = {}

    # ============ KV Index Registry ============

    _kv_registry: dict[str, type[BaseKVIndex]] = {
        "bm25": BM25sIndex,
        "bm25s": BM25sIndex,
    }

    # ============ Graph Index Registry ============

    _graph_registry: dict[str, type[BaseGraphIndex]] = {
        "simple": SimpleGraphIndex,
        "adjacency": SimpleGraphIndex,
    }

    # ============ VDB Index Methods ============

    @classmethod
    def create_vdb_index(cls, config: dict[str, Any]) -> BaseVDBIndex:
        """
        Create a VDB (vector database) index.

        Args:
            config: Configuration dict with keys:
                - name: Index name (required)
                - dim: Vector dimension (required)
                - backend_type: Backend type ("faiss", default: "faiss")
                - index_type: FAISS index type (default: "IndexFlatIP")
                - Other backend-specific parameters

        Returns:
            Created VDB index

        Example:
            index = IndexFactory.create_vdb_index({
                "name": "my_index",
                "dim": 768,
                "backend_type": "faiss",
                "index_type": "IndexHNSWFlat",
                "HNSW_M": 32,
            })
        """
        # Delegate to VDBIndexFactory which handles FAISS registration
        factory = VDBIndexFactory()
        return factory.create_index(config)

    @classmethod
    def load_vdb_index(cls, name: str, dir_path: str, backend_type: str = "faiss") -> BaseVDBIndex:
        """
        Load a VDB index from disk.

        Args:
            name: Index name
            dir_path: Directory to load from
            backend_type: Backend type

        Returns:
            Loaded VDB index
        """
        backend_type = backend_type.upper()
        if backend_type == "FAISS":
            from .vdb_index.faiss_index import FaissIndex

            return FaissIndex.load(name, dir_path)
        raise ValueError(f"Unknown VDB backend: {backend_type}")

    # ============ KV Index Methods ============

    @classmethod
    def create_kv_index(cls, config: dict[str, Any]) -> BaseKVIndex:
        """
        Create a KV (key-value/text) index.

        Args:
            config: Configuration dict with keys:
                - name: Index name (required)
                - index_type: Index type ("bm25s", default: "bm25s")
                - language: Language for tokenization ("auto", "zh", "en")
                - Other index-specific parameters

        Returns:
            Created KV index

        Example:
            index = IndexFactory.create_kv_index({
                "name": "my_index",
                "index_type": "bm25s",
                "language": "zh",
            })
        """
        name = config.get("name")
        if not name:
            raise ValueError("Config must contain 'name'")

        index_type = config.get("index_type", "bm25s").lower()
        if index_type not in cls._kv_registry:
            raise ValueError(f"Unknown KV index type: {index_type}")

        index_class = cls._kv_registry[index_type]
        return index_class(config=config)

    @classmethod
    def load_kv_index(cls, name: str, dir_path: str, index_type: str = "bm25s") -> BaseKVIndex:
        """
        Load a KV index from disk.

        Args:
            name: Index name
            dir_path: Directory to load from
            index_type: Index type

        Returns:
            Loaded KV index
        """
        return KVIndexFactory.load_index(index_type, name, dir_path)

    # ============ Graph Index Methods ============

    @classmethod
    def create_graph_index(cls, config: dict[str, Any]) -> BaseGraphIndex:
        """
        Create a graph index.

        Args:
            config: Configuration dict with keys:
                - name: Index name (required)
                - index_type: Index type ("simple", "adjacency", default: "simple")

        Returns:
            Created graph index

        Example:
            index = IndexFactory.create_graph_index({
                "name": "my_graph",
                "index_type": "simple",
            })
        """
        return GraphIndexFactory.create(config)

    @classmethod
    def load_graph_index(
        cls, name: str, dir_path: str, index_type: str = "simple"
    ) -> BaseGraphIndex:
        """
        Load a graph index from disk.

        Args:
            name: Index name
            dir_path: Directory to load from
            index_type: Index type

        Returns:
            Loaded graph index
        """
        return GraphIndexFactory.load(name, dir_path, index_type)

    # ============ Registry Management ============

    @classmethod
    def register_vdb(cls, name: str, index_class: type[BaseVDBIndex]) -> None:
        """
        Register a new VDB index type.

        Args:
            name: Type name
            index_class: Index class
        """
        VDBIndexFactory.register_index(name.upper(), index_class)

    @classmethod
    def register_kv(cls, name: str, index_class: type[BaseKVIndex]) -> None:
        """
        Register a new KV index type.

        Args:
            name: Type name
            index_class: Index class
        """
        cls._kv_registry[name.lower()] = index_class
        KVIndexFactory.register_index_type(name.lower(), index_class)

    @classmethod
    def register_graph(cls, name: str, index_class: type[BaseGraphIndex]) -> None:
        """
        Register a new graph index type.

        Args:
            name: Type name
            index_class: Index class
        """
        cls._graph_registry[name.lower()] = index_class
        GraphIndexFactory.register(name.lower(), index_class)

    @classmethod
    def get_supported_vdb_types(cls) -> list[str]:
        """Get all supported VDB index types."""
        return list(VDBIndexFactory._index_registry.keys())

    @classmethod
    def get_supported_kv_types(cls) -> list[str]:
        """Get all supported KV index types."""
        return list(cls._kv_registry.keys())

    @classmethod
    def get_supported_graph_types(cls) -> list[str]:
        """Get all supported graph index types."""
        return list(cls._graph_registry.keys())


# Export factory as module-level function for convenience
def create_vdb_index(config: dict[str, Any]) -> BaseVDBIndex:
    """Create a VDB index. See IndexFactory.create_vdb_index for details."""
    return IndexFactory.create_vdb_index(config)


def create_kv_index(config: dict[str, Any]) -> BaseKVIndex:
    """Create a KV index. See IndexFactory.create_kv_index for details."""
    return IndexFactory.create_kv_index(config)


def create_graph_index(config: dict[str, Any]) -> BaseGraphIndex:
    """Create a graph index. See IndexFactory.create_graph_index for details."""
    return IndexFactory.create_graph_index(config)
