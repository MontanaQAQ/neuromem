"""
Graph-based memory collection implementation.

Provides graph-based memory storage with nodes and weighted edges.
"""

import json
import logging
from collections import deque
from pathlib import Path
from typing import Any

from ..utils.path_utils import get_default_data_dir
from .base_collection import BaseMemoryCollection


class SimpleGraphIndex:
    """
    Simple in-memory graph index using adjacency lists.

    Stores a weighted directed graph with:
    - Nodes: identified by string IDs with associated data
    - Edges: weighted directed edges between nodes
    - Bidirectional tracking for efficient neighbor queries
    """

    def __init__(self, name: str):
        """
        Initialize graph index.

        Args:
            name: Name of the index
        """
        self.name = name
        # Adjacency lists: node_id -> [(neighbor_id, weight), ...]
        self.adjacency: dict[str, list[tuple[str, float]]] = {}
        # Reverse adjacency for incoming edges
        self.reverse_adjacency: dict[str, list[tuple[str, float]]] = {}
        # Node data storage
        self.nodes: dict[str, Any] = {}

    def add_node(self, node_id: str, data: Any = None) -> None:
        """
        Add or update a node.

        Args:
            node_id: Unique identifier for the node
            data: Data associated with the node
        """
        if node_id not in self.nodes:
            self.adjacency[node_id] = []
            self.reverse_adjacency[node_id] = []
        self.nodes[node_id] = data

    def add_edge(self, from_node: str, to_node: str, weight: float = 1.0) -> None:
        """
        Add a directed edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            weight: Edge weight (default: 1.0)
        """
        # Ensure nodes exist
        if from_node not in self.nodes:
            self.add_node(from_node)
        if to_node not in self.nodes:
            self.add_node(to_node)

        # Add edge (update if exists)
        edges = self.adjacency[from_node]
        # Remove existing edge if present
        self.adjacency[from_node] = [(n, w) for n, w in edges if n != to_node]
        self.adjacency[from_node].append((to_node, weight))

        # Add reverse edge
        rev_edges = self.reverse_adjacency[to_node]
        self.reverse_adjacency[to_node] = [(n, w) for n, w in rev_edges if n != from_node]
        self.reverse_adjacency[to_node].append((from_node, weight))

    def remove_node(self, node_id: str) -> None:
        """
        Remove a node and all its edges.

        Args:
            node_id: Node ID to remove
        """
        if node_id not in self.nodes:
            return

        # Remove all outgoing edges
        for neighbor, _ in self.adjacency[node_id]:
            # Remove from reverse adjacency
            self.reverse_adjacency[neighbor] = [
                (n, w) for n, w in self.reverse_adjacency[neighbor] if n != node_id
            ]

        # Remove all incoming edges
        for source, _ in self.reverse_adjacency[node_id]:
            # Remove from adjacency
            self.adjacency[source] = [(n, w) for n, w in self.adjacency[source] if n != node_id]

        # Remove node data and adjacency lists
        del self.nodes[node_id]
        del self.adjacency[node_id]
        del self.reverse_adjacency[node_id]

    def remove_edge(self, from_node: str, to_node: str) -> None:
        """
        Remove an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
        """
        if from_node in self.adjacency:
            self.adjacency[from_node] = [
                (n, w) for n, w in self.adjacency[from_node] if n != to_node
            ]

        if to_node in self.reverse_adjacency:
            self.reverse_adjacency[to_node] = [
                (n, w) for n, w in self.reverse_adjacency[to_node] if n != from_node
            ]

    def get_neighbors(self, node_id: str, k: int = 10) -> list[str]:
        """
        Get top-k neighbors sorted by edge weight (descending).

        Args:
            node_id: Node ID to get neighbors for
            k: Maximum number of neighbors to return

        Returns:
            List of neighbor node IDs sorted by weight
        """
        if node_id not in self.adjacency:
            return []

        neighbors = self.adjacency[node_id]
        # Sort by weight descending
        sorted_neighbors = sorted(neighbors, key=lambda x: x[1], reverse=True)
        return [n for n, _ in sorted_neighbors[:k]]

    def get_incoming_neighbors(self, node_id: str, k: int = 10) -> list[str]:
        """
        Get top-k incoming neighbors (nodes with edges to this node).

        Args:
            node_id: Node ID to get incoming neighbors for
            k: Maximum number of neighbors to return

        Returns:
            List of source node IDs sorted by weight
        """
        if node_id not in self.reverse_adjacency:
            return []

        neighbors = self.reverse_adjacency[node_id]
        sorted_neighbors = sorted(neighbors, key=lambda x: x[1], reverse=True)
        return [n for n, _ in sorted_neighbors[:k]]

    def has_node(self, node_id: str) -> bool:
        """
        Check if a node exists.

        Args:
            node_id: Node ID to check

        Returns:
            True if node exists
        """
        return node_id in self.nodes

    def get_node_data(self, node_id: str) -> Any:
        """
        Get data associated with a node.

        Args:
            node_id: Node ID

        Returns:
            Node data or None if not found
        """
        return self.nodes.get(node_id)

    def store(self, directory: Path) -> dict[str, Any]:
        """
        Save graph to disk.

        Args:
            directory: Directory to save to

        Returns:
            Storage metadata
        """
        directory.mkdir(parents=True, exist_ok=True)

        # Save nodes
        nodes_file = directory / "nodes.json"
        with open(nodes_file, "w", encoding="utf-8") as f:
            json.dump(self.nodes, f, indent=2)

        # Save edges (only adjacency needed, reverse can be reconstructed)
        edges_data = {node_id: list(neighbors) for node_id, neighbors in self.adjacency.items()}
        edges_file = directory / "edges.json"
        with open(edges_file, "w", encoding="utf-8") as f:
            json.dump(edges_data, f, indent=2)

        return {
            "nodes_file": str(nodes_file),
            "edges_file": str(edges_file),
            "node_count": len(self.nodes),
            "edge_count": sum(len(edges) for edges in self.adjacency.values()),
        }

    @classmethod
    def load(cls, name: str, directory: Path) -> "SimpleGraphIndex":
        """
        Load graph from disk.

        Args:
            name: Index name
            directory: Directory to load from

        Returns:
            Loaded graph index
        """
        index = cls(name)

        # Load nodes
        nodes_file = directory / "nodes.json"
        if nodes_file.exists():
            with open(nodes_file, encoding="utf-8") as f:
                index.nodes = json.load(f)

        # Load edges
        edges_file = directory / "edges.json"
        if edges_file.exists():
            with open(edges_file, encoding="utf-8") as f:
                edges_data = json.load(f)

            # Reconstruct adjacency lists
            for node_id in index.nodes:
                index.adjacency[node_id] = []
                index.reverse_adjacency[node_id] = []

            for from_node, neighbors in edges_data.items():
                index.adjacency[from_node] = list(neighbors)
                for to_node, weight in neighbors:
                    index.reverse_adjacency[to_node].append((from_node, weight))

        return index


class GraphMemoryCollection(BaseMemoryCollection):
    """
    Graph-based memory collection.

    Stores documents with graph relationships for knowledge graph RAG.
    Combines text/metadata storage with graph structure.
    """

    def __init__(self, name: str, **kwargs: Any):
        """
        Initialize graph memory collection.

        Args:
            name: Collection name
            **kwargs: Additional arguments
        """
        super().__init__(name)
        self.indexes: dict[str, SimpleGraphIndex] = {}
        self.logger = logging.getLogger(__name__)
        self.description = kwargs.get("description", "")

    def create_index(self, config: dict[str, Any]) -> bool:
        """
        Create a new graph index.

        Args:
            config: Index configuration with 'name' key

        Returns:
            True if created, False if already exists
        """
        index_name = config.get("name", "default")

        if index_name in self.indexes:
            self.logger.warning(f"Index '{index_name}' already exists")
            return False

        self.indexes[index_name] = SimpleGraphIndex(index_name)
        self.logger.info(f"Created graph index: {index_name}")
        return True

    def delete_index(self, index_name: str) -> bool:
        """
        Delete a graph index.

        Args:
            index_name: Name of index to delete

        Returns:
            True if deleted, False if not found
        """
        if index_name not in self.indexes:
            return False

        del self.indexes[index_name]
        self.logger.info(f"Deleted graph index: {index_name}")
        return True

    def add_node(
        self,
        node_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        index_name: str = "default",
    ) -> str:
        """
        Add a node to the graph.

        Args:
            node_id: Unique node identifier
            text: Text content for the node
            metadata: Optional metadata
            index_name: Graph index to add to

        Returns:
            Node ID
        """
        # Store text and metadata using base collection
        self.text_storage.store(node_id, text)
        if metadata:
            # Register metadata fields if needed
            for field in metadata:
                if not self.metadata_storage.has_field(field):
                    self.metadata_storage.add_field(field)
            self.metadata_storage.store(node_id, metadata)

        # Add to graph index
        if index_name not in self.indexes:
            self.create_index({"name": index_name})

        self.indexes[index_name].add_node(node_id, text)
        return node_id

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        weight: float = 1.0,
        index_name: str = "default",
    ) -> None:
        """
        Add an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            weight: Edge weight
            index_name: Graph index to add to
        """
        if index_name not in self.indexes:
            self.create_index({"name": index_name})

        self.indexes[index_name].add_edge(from_node, to_node, weight)

    def get_neighbors(
        self, node_id: str, k: int = 10, index_name: str = "default"
    ) -> list[dict[str, Any]]:
        """
        Get neighbors of a node.

        Args:
            node_id: Node ID to get neighbors for
            k: Maximum number of neighbors
            index_name: Graph index to query

        Returns:
            List of neighbor dicts with 'node_id' and 'data'
        """
        if index_name not in self.indexes:
            return []

        neighbor_ids = self.indexes[index_name].get_neighbors(node_id, k)
        return [
            {"node_id": nid, "data": self.indexes[index_name].get_node_data(nid)}
            for nid in neighbor_ids
        ]

    def retrieve_by_graph(
        self,
        start_node: str,
        max_depth: int = 2,
        max_nodes: int = 10,
        index_name: str = "default",
    ) -> list[dict[str, Any]]:
        """
        Retrieve nodes via BFS graph traversal.

        Args:
            start_node: Starting node ID
            max_depth: Maximum traversal depth
            max_nodes: Maximum nodes to return
            index_name: Graph index to traverse

        Returns:
            List of node dicts with 'node_id', 'data', 'depth'
        """
        if index_name not in self.indexes:
            return []

        index = self.indexes[index_name]
        if not index.has_node(start_node):
            return []

        visited = set()
        results = []
        queue = deque([(start_node, 0)])  # (node_id, depth)

        while queue and len(results) < max_nodes:
            node_id, depth = queue.popleft()

            if node_id in visited or depth > max_depth:
                continue

            visited.add(node_id)
            results.append(
                {
                    "node_id": node_id,
                    "data": index.get_node_data(node_id),
                    "depth": depth,
                }
            )

            if depth < max_depth:
                neighbors = index.get_neighbors(node_id, k=100)
                for neighbor_id in neighbors:
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, depth + 1))

        return results

    def store(self, data_dir: str | None = None) -> dict[str, Any]:
        """
        Save collection to disk.

        Args:
            data_dir: Optional data directory

        Returns:
            Storage metadata
        """
        if data_dir is None:
            data_dir = get_default_data_dir()

        collection_path = Path(data_dir) / "graph_collection" / self.name
        collection_path.mkdir(parents=True, exist_ok=True)

        # Store config
        config = {
            "name": self.name,
            "backend_type": "graph",
            "description": self.description,
        }
        with open(collection_path / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Store text storage
        text_data = {
            text_id: self.text_storage.get(text_id) for text_id in self.text_storage.get_all_ids()
        }
        with open(collection_path / "text_storage.json", "w", encoding="utf-8") as f:
            json.dump(text_data, f, indent=2)

        # Store metadata - get all IDs and their metadata
        metadata_ids = self.get_all_ids()
        metadata_data = {"store": {mid: self.metadata_storage.get(mid) for mid in metadata_ids}}
        with open(collection_path / "metadata_storage.json", "w", encoding="utf-8") as f:
            json.dump(metadata_data, f, indent=2)

        # Store graph indexes
        indexes_dir = collection_path / "indexes"
        indexes_dir.mkdir(parents=True, exist_ok=True)

        for index_name, index in self.indexes.items():
            index_dir = indexes_dir / index_name
            index.store(index_dir)

        return {
            "collection_path": str(collection_path),
            "node_count": len(self.get_all_ids()),
            "index_count": len(self.indexes),
        }

    @classmethod
    def load(cls, name: str, data_dir: str | None = None) -> "GraphMemoryCollection":
        """
        Load collection from disk.

        Args:
            name: Collection name
            data_dir: Data directory (can be base dir or collection dir)

        Returns:
            Loaded collection
        """
        if data_dir is None:
            data_dir = get_default_data_dir()

        # Handle both full path and base path
        collection_path = Path(data_dir)
        if not (collection_path / "config.json").exists():
            # data_dir is base directory, append collection path
            collection_path = collection_path / "graph_collection" / name

        # Load base collection
        collection = cls(name)

        # Load config
        config_file = collection_path / "config.json"
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                config = json.load(f)
            collection.description = config.get("description", "")

        # Load text storage
        text_file = collection_path / "text_storage.json"
        if text_file.exists():
            with open(text_file, encoding="utf-8") as f:
                text_data = json.load(f)
            for text_id, text in text_data.items():
                collection.text_storage.store(text_id, text)

        # Load metadata
        metadata_file = collection_path / "metadata_storage.json"
        if metadata_file.exists():
            with open(metadata_file, encoding="utf-8") as f:
                metadata_data = json.load(f)
            # Restore metadata store
            if "store" in metadata_data:
                for meta_id, meta in metadata_data["store"].items():
                    # Register fields
                    for field in meta:
                        if not collection.metadata_storage.has_field(field):
                            collection.metadata_storage.add_field(field)
                    # Store metadata
                    collection.metadata_storage.store(meta_id, meta)

        # Load graph indexes
        indexes_dir = collection_path / "indexes"
        if indexes_dir.exists():
            for index_dir in indexes_dir.iterdir():
                if index_dir.is_dir():
                    index_name = index_dir.name
                    collection.indexes[index_name] = SimpleGraphIndex.load(index_name, index_dir)

        return collection
