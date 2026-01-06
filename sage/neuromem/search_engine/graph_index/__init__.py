"""
Graph Index module for NeuroMem.

Provides graph-based indexing with support for:
- Node and edge management
- Weighted directed graphs
- Neighbor queries (outgoing, incoming, both)
- Graph traversal (BFS, DFS)
- Personalized PageRank (PPR) for HippoRAG
"""

from .base_graph_index import BaseGraphIndex
from .simple_graph_index import SimpleGraphIndex


class GraphIndexFactory:
    """
    Factory for creating graph indexes.
    """

    _registry: dict[str, type[BaseGraphIndex]] = {
        "simple": SimpleGraphIndex,
        "adjacency": SimpleGraphIndex,
    }

    @classmethod
    def create(cls, config: dict) -> BaseGraphIndex:
        """
        Create a graph index from configuration.

        Args:
            config: Configuration dict with keys:
                - name: Index name (required)
                - index_type: Type of index ("simple", "adjacency")

        Returns:
            Created graph index
        """
        name = config.get("name")
        if not name:
            raise ValueError("Config must contain 'name'")

        index_type = config.get("index_type", "simple").lower()
        if index_type not in cls._registry:
            raise ValueError(f"Unknown graph index type: {index_type}")

        index_class = cls._registry[index_type]
        return index_class(name=name, config=config)

    @classmethod
    def load(cls, name: str, dir_path: str, index_type: str = "simple") -> BaseGraphIndex:
        """
        Load a graph index from disk.

        Args:
            name: Index name
            dir_path: Directory to load from
            index_type: Type of index

        Returns:
            Loaded graph index
        """
        index_type = index_type.lower()
        if index_type not in cls._registry:
            raise ValueError(f"Unknown graph index type: {index_type}")

        index_class = cls._registry[index_type]
        return index_class.load(name, dir_path)

    @classmethod
    def register(cls, name: str, index_class: type[BaseGraphIndex]) -> None:
        """
        Register a new graph index type.

        Args:
            name: Type name
            index_class: Index class
        """
        cls._registry[name.lower()] = index_class

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get all supported index types."""
        return list(cls._registry.keys())


__all__ = [
    "BaseGraphIndex",
    "SimpleGraphIndex",
    "GraphIndexFactory",
]
