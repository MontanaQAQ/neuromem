"""
Base class for graph indexes.

Graph indexes store nodes with data and weighted directed edges.
Supports neighbor queries, graph traversal, and PPR algorithms.
"""

import contextlib
from abc import ABC, abstractmethod
from typing import Any, Literal


class BaseGraphIndex(ABC):
    """
    Abstract base class for graph indexes.

    Provides interface for:
    - Node management (add, remove, update)
    - Edge management (add, remove, update weight)
    - Neighbor queries (outgoing, incoming, both)
    - Graph traversal (BFS, DFS)
    - Personalized PageRank (PPR) for HippoRAG support
    - Persistence (store/load)
    """

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        """
        Initialize graph index.

        Args:
            name: Index name
            config: Optional configuration
        """
        self.name = name
        self.config = config or {}

    # ============ Node Operations ============

    @abstractmethod
    def add_node(self, node_id: str, data: Any = None) -> bool:
        """
        Add a node to the graph.

        Args:
            node_id: Unique identifier for the node
            data: Optional data associated with the node

        Returns:
            True if node was added, False if already exists
        """
        ...

    @abstractmethod
    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node and all its edges.

        Args:
            node_id: Node ID to remove

        Returns:
            True if removed, False if not found
        """
        ...

    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """
        Check if a node exists.

        Args:
            node_id: Node ID to check

        Returns:
            True if node exists
        """
        ...

    @abstractmethod
    def get_node_data(self, node_id: str) -> Any:
        """
        Get data associated with a node.

        Args:
            node_id: Node ID

        Returns:
            Node data or None if not found
        """
        ...

    @abstractmethod
    def update_node_data(self, node_id: str, data: Any) -> bool:
        """
        Update the data associated with a node.

        Args:
            node_id: Node ID
            data: New data for the node

        Returns:
            True if updated, False if node not found
        """
        ...

    # ============ Edge Operations ============

    @abstractmethod
    def add_edge(
        self,
        from_node: str,
        to_node: str,
        weight: float = 1.0,
        relation: str | None = None,
    ) -> bool:
        """
        Add a directed edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            weight: Edge weight (default: 1.0)
            relation: Optional relation type/name for the edge

        Returns:
            True if edge was added/updated
        """
        ...

    @abstractmethod
    def remove_edge(self, from_node: str, to_node: str) -> bool:
        """
        Remove an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            True if removed, False if not found
        """
        ...

    @abstractmethod
    def has_edge(self, from_node: str, to_node: str) -> bool:
        """
        Check if an edge exists.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            True if edge exists
        """
        ...

    @abstractmethod
    def get_edge_weight(self, from_node: str, to_node: str) -> float | None:
        """
        Get the weight of an edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            Edge weight or None if edge not found
        """
        ...

    @abstractmethod
    def update_edge_weight(
        self,
        from_node: str,
        to_node: str,
        new_weight: float,
    ) -> bool:
        """
        Update the weight of an edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            new_weight: New weight value

        Returns:
            True if updated, False if edge not found
        """
        ...

    @abstractmethod
    def get_edge_relation(self, from_node: str, to_node: str) -> str | None:
        """
        Get the relation type of an edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            Relation type or None if not set
        """
        ...

    # ============ Neighbor Queries ============

    @abstractmethod
    def get_neighbors(
        self,
        node_id: str,
        k: int = 10,
        direction: Literal["outgoing", "incoming", "both"] = "outgoing",
    ) -> list[tuple[str, float]]:
        """
        Get neighbors of a node.

        Args:
            node_id: Node ID
            k: Maximum number of neighbors to return
            direction: Direction of edges to consider
                - "outgoing": edges from this node
                - "incoming": edges to this node
                - "both": all connected edges

        Returns:
            List of (neighbor_id, weight) tuples sorted by weight descending
        """
        ...

    @abstractmethod
    def get_edges_by_relation(
        self,
        node_id: str,
        relation: str,
        direction: Literal["outgoing", "incoming", "both"] = "outgoing",
    ) -> list[tuple[str, float]]:
        """
        Get neighbors connected by a specific relation type.

        Args:
            node_id: Node ID
            relation: Relation type to filter by
            direction: Direction of edges

        Returns:
            List of (neighbor_id, weight) tuples
        """
        ...

    # ============ Graph Traversal ============

    @abstractmethod
    def traverse_bfs(
        self,
        start_node: str,
        max_depth: int = 2,
        max_nodes: int = 100,
    ) -> list[str]:
        """
        BFS traversal from a starting node.

        Args:
            start_node: Starting node ID
            max_depth: Maximum traversal depth
            max_nodes: Maximum number of nodes to return

        Returns:
            List of node IDs in BFS order
        """
        ...

    @abstractmethod
    def traverse_dfs(
        self,
        start_node: str,
        max_depth: int = 2,
        max_nodes: int = 100,
    ) -> list[str]:
        """
        DFS traversal from a starting node.

        Args:
            start_node: Starting node ID
            max_depth: Maximum traversal depth
            max_nodes: Maximum number of nodes to return

        Returns:
            List of node IDs in DFS order
        """
        ...

    # ============ PPR Algorithm (HippoRAG Support) ============

    @abstractmethod
    def ppr(
        self,
        seed_nodes: list[str],
        alpha: float = 0.15,
        max_iter: int = 100,
        top_k: int = 10,
        epsilon: float = 1e-6,
    ) -> list[tuple[str, float]]:
        """
        Personalized PageRank algorithm.

        Computes the PPR scores starting from seed nodes,
        using power iteration method.

        Args:
            seed_nodes: List of seed node IDs (starting points)
            alpha: Teleport probability (restart probability)
            max_iter: Maximum number of iterations
            top_k: Number of top-scoring nodes to return
            epsilon: Convergence threshold

        Returns:
            List of (node_id, score) tuples sorted by score descending
        """
        ...

    # ============ Statistics ============

    @abstractmethod
    def node_count(self) -> int:
        """
        Get the number of nodes in the graph.

        Returns:
            Number of nodes
        """
        ...

    @abstractmethod
    def edge_count(self) -> int:
        """
        Get the number of edges in the graph.

        Returns:
            Number of edges
        """
        ...

    @abstractmethod
    def get_all_node_ids(self) -> list[str]:
        """
        Get all node IDs in the graph.

        Returns:
            List of all node IDs
        """
        ...

    # ============ Persistence ============

    @abstractmethod
    def store(self, dir_path: str) -> dict[str, Any]:
        """
        Save graph index to disk.

        Args:
            dir_path: Directory path to save to

        Returns:
            Storage metadata
        """
        ...

    @classmethod
    @abstractmethod
    def load(cls, name: str, dir_path: str) -> "BaseGraphIndex":
        """
        Load graph index from disk.

        Args:
            name: Index name
            dir_path: Directory path to load from

        Returns:
            Loaded graph index
        """
        ...

    @staticmethod
    def clear(dir_path: str) -> None:
        """
        Clear stored index data.

        Args:
            dir_path: Directory path to clear
        """
        import shutil

        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(dir_path)
