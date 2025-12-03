"""
Simple in-memory graph index implementation.

Uses adjacency lists for efficient neighbor queries and supports
bidirectional edge tracking, BFS/DFS traversal, and PPR algorithm.
"""

import contextlib
import json
import shutil
from collections import deque
from pathlib import Path
from typing import Any, Literal

from .base_graph_index import BaseGraphIndex


class SimpleGraphIndex(BaseGraphIndex):
    """
    Simple in-memory graph index using adjacency lists.

    Stores a weighted directed graph with:
    - Nodes: identified by string IDs with associated data
    - Edges: weighted directed edges between nodes with optional relation type
    - Bidirectional tracking for efficient neighbor queries

    Edge storage format:
        adjacency[from_node] = [(to_node, weight, relation), ...]
    """

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        """
        Initialize graph index.

        Args:
            name: Name of the index
            config: Optional configuration
        """
        super().__init__(name, config)

        # Adjacency lists: node_id -> [(neighbor_id, weight, relation), ...]
        self.adjacency: dict[str, list[tuple[str, float, str | None]]] = {}
        # Reverse adjacency for incoming edges
        self.reverse_adjacency: dict[str, list[tuple[str, float, str | None]]] = {}
        # Node data storage
        self.nodes: dict[str, Any] = {}

    # ============ Node Operations ============

    def add_node(self, node_id: str, data: Any = None) -> bool:
        """
        Add or update a node.

        Args:
            node_id: Unique identifier for the node
            data: Data associated with the node

        Returns:
            True if node was newly added, False if updated
        """
        is_new = node_id not in self.nodes
        if is_new:
            self.adjacency[node_id] = []
            self.reverse_adjacency[node_id] = []
        self.nodes[node_id] = data
        return is_new

    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node and all its edges.

        Args:
            node_id: Node ID to remove

        Returns:
            True if removed, False if not found
        """
        if node_id not in self.nodes:
            return False

        # Remove all outgoing edges
        for neighbor, _, _ in self.adjacency[node_id]:
            # Remove from reverse adjacency
            self.reverse_adjacency[neighbor] = [
                (n, w, r) for n, w, r in self.reverse_adjacency[neighbor] if n != node_id
            ]

        # Remove all incoming edges
        for source, _, _ in self.reverse_adjacency[node_id]:
            # Remove from adjacency
            self.adjacency[source] = [
                (n, w, r) for n, w, r in self.adjacency[source] if n != node_id
            ]

        # Remove node data and adjacency lists
        del self.nodes[node_id]
        del self.adjacency[node_id]
        del self.reverse_adjacency[node_id]
        return True

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

    def update_node_data(self, node_id: str, data: Any) -> bool:
        """
        Update the data associated with a node.

        Args:
            node_id: Node ID
            data: New data for the node

        Returns:
            True if updated, False if node not found
        """
        if node_id not in self.nodes:
            return False
        self.nodes[node_id] = data
        return True

    # ============ Edge Operations ============

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
            True (edge always added/updated)
        """
        # Ensure nodes exist
        if from_node not in self.nodes:
            self.add_node(from_node)
        if to_node not in self.nodes:
            self.add_node(to_node)

        # Remove existing edge if present
        self.adjacency[from_node] = [
            (n, w, r) for n, w, r in self.adjacency[from_node] if n != to_node
        ]
        self.adjacency[from_node].append((to_node, weight, relation))

        # Update reverse adjacency
        self.reverse_adjacency[to_node] = [
            (n, w, r) for n, w, r in self.reverse_adjacency[to_node] if n != from_node
        ]
        self.reverse_adjacency[to_node].append((from_node, weight, relation))

        return True

    def remove_edge(self, from_node: str, to_node: str) -> bool:
        """
        Remove an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            True if removed, False if not found
        """
        if from_node not in self.adjacency:
            return False

        # Check if edge exists
        original_len = len(self.adjacency[from_node])
        self.adjacency[from_node] = [
            (n, w, r) for n, w, r in self.adjacency[from_node] if n != to_node
        ]

        if len(self.adjacency[from_node]) == original_len:
            return False  # Edge was not found

        # Remove from reverse adjacency
        if to_node in self.reverse_adjacency:
            self.reverse_adjacency[to_node] = [
                (n, w, r) for n, w, r in self.reverse_adjacency[to_node] if n != from_node
            ]

        return True

    def has_edge(self, from_node: str, to_node: str) -> bool:
        """
        Check if an edge exists.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            True if edge exists
        """
        if from_node not in self.adjacency:
            return False
        return any(n == to_node for n, _, _ in self.adjacency[from_node])

    def get_edge_weight(self, from_node: str, to_node: str) -> float | None:
        """
        Get the weight of an edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            Edge weight or None if edge not found
        """
        if from_node not in self.adjacency:
            return None
        for n, w, _ in self.adjacency[from_node]:
            if n == to_node:
                return w
        return None

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
        if from_node not in self.adjacency:
            return False

        # Update in adjacency
        found = False
        new_edges = []
        for n, w, r in self.adjacency[from_node]:
            if n == to_node:
                new_edges.append((n, new_weight, r))
                found = True
            else:
                new_edges.append((n, w, r))
        self.adjacency[from_node] = new_edges

        if not found:
            return False

        # Update in reverse adjacency
        if to_node in self.reverse_adjacency:
            new_rev_edges = []
            for n, w, r in self.reverse_adjacency[to_node]:
                if n == from_node:
                    new_rev_edges.append((n, new_weight, r))
                else:
                    new_rev_edges.append((n, w, r))
            self.reverse_adjacency[to_node] = new_rev_edges

        return True

    def get_edge_relation(self, from_node: str, to_node: str) -> str | None:
        """
        Get the relation type of an edge.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            Relation type or None if not set
        """
        if from_node not in self.adjacency:
            return None
        for n, _, r in self.adjacency[from_node]:
            if n == to_node:
                return r
        return None

    # ============ Neighbor Queries ============

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

        Returns:
            List of (neighbor_id, weight) tuples sorted by weight descending
        """
        if node_id not in self.nodes:
            return []

        neighbors: list[tuple[str, float]] = []

        if direction in ("outgoing", "both"):
            for n, w, _ in self.adjacency.get(node_id, []):
                neighbors.append((n, w))

        if direction in ("incoming", "both"):
            for n, w, _ in self.reverse_adjacency.get(node_id, []):
                # Avoid duplicates when direction is "both"
                if direction == "both" and any(n == existing[0] for existing in neighbors):
                    continue
                neighbors.append((n, w))

        # Sort by weight descending and limit to k
        neighbors.sort(key=lambda x: x[1], reverse=True)
        return neighbors[:k]

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
        if node_id not in self.nodes:
            return []

        neighbors: list[tuple[str, float]] = []

        if direction in ("outgoing", "both"):
            for n, w, r in self.adjacency.get(node_id, []):
                if r == relation:
                    neighbors.append((n, w))

        if direction in ("incoming", "both"):
            for n, w, r in self.reverse_adjacency.get(node_id, []):
                if r == relation:
                    # Avoid duplicates
                    if direction == "both" and any(n == existing[0] for existing in neighbors):
                        continue
                    neighbors.append((n, w))

        return neighbors

    # ============ Graph Traversal ============

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
        if not self.has_node(start_node):
            return []

        visited: set[str] = set()
        result: list[str] = []
        queue: deque[tuple[str, int]] = deque([(start_node, 0)])

        while queue and len(result) < max_nodes:
            node_id, depth = queue.popleft()

            if node_id in visited or depth > max_depth:
                continue

            visited.add(node_id)
            result.append(node_id)

            if depth < max_depth:
                for neighbor, _, _ in self.adjacency.get(node_id, []):
                    if neighbor not in visited:
                        queue.append((neighbor, depth + 1))

        return result

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
        if not self.has_node(start_node):
            return []

        visited: set[str] = set()
        result: list[str] = []

        def dfs(node_id: str, depth: int) -> None:
            if len(result) >= max_nodes or depth > max_depth or node_id in visited:
                return

            visited.add(node_id)
            result.append(node_id)

            for neighbor, _, _ in self.adjacency.get(node_id, []):
                if neighbor not in visited:
                    dfs(neighbor, depth + 1)

        dfs(start_node, 0)
        return result

    # ============ PPR Algorithm (HippoRAG Support) ============

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

        Uses power iteration to compute PPR scores from seed nodes.
        The algorithm computes: PPR = alpha * seed + (1-alpha) * M * PPR
        where M is the row-normalized adjacency matrix.

        Args:
            seed_nodes: List of seed node IDs (starting points)
            alpha: Teleport probability (restart probability)
            max_iter: Maximum number of iterations
            top_k: Number of top-scoring nodes to return
            epsilon: Convergence threshold

        Returns:
            List of (node_id, score) tuples sorted by score descending
        """
        if not seed_nodes or not self.nodes:
            return []

        # Filter to valid seed nodes
        valid_seeds = [n for n in seed_nodes if n in self.nodes]
        if not valid_seeds:
            return []

        all_nodes = list(self.nodes.keys())
        n = len(all_nodes)
        node_to_idx = {node: i for i, node in enumerate(all_nodes)}

        # Initialize scores
        scores = [0.0] * n

        # Initialize seed distribution (uniform over seed nodes)
        seed_dist = [0.0] * n
        for seed in valid_seeds:
            if seed in node_to_idx:
                seed_dist[node_to_idx[seed]] = 1.0 / len(valid_seeds)

        # Initialize with seed distribution
        scores = list(seed_dist)

        # Power iteration
        for _ in range(max_iter):
            new_scores = [0.0] * n

            # Random walk contribution: (1-alpha) * M * scores
            for node_id, node_idx in node_to_idx.items():
                neighbors = self.adjacency.get(node_id, [])
                if neighbors:
                    # Distribute score equally among neighbors
                    out_score = scores[node_idx] / len(neighbors)
                    for neighbor, weight, _ in neighbors:
                        if neighbor in node_to_idx:
                            # Weight-normalized contribution
                            total_weight = sum(w for _, w, _ in neighbors)
                            contrib = (
                                scores[node_idx] * (weight / total_weight)
                                if total_weight > 0
                                else out_score
                            )
                            new_scores[node_to_idx[neighbor]] += (1 - alpha) * contrib

            # Teleport contribution: alpha * seed_dist
            for i in range(n):
                new_scores[i] += alpha * seed_dist[i]

            # Check convergence
            diff = sum(abs(new_scores[i] - scores[i]) for i in range(n))
            scores = new_scores

            if diff < epsilon:
                break

        # Return top-k nodes sorted by score
        result = [(all_nodes[i], scores[i]) for i in range(n) if scores[i] > 0]
        result.sort(key=lambda x: x[1], reverse=True)
        return result[:top_k]

    # ============ Statistics ============

    def node_count(self) -> int:
        """
        Get the number of nodes in the graph.

        Returns:
            Number of nodes
        """
        return len(self.nodes)

    def edge_count(self) -> int:
        """
        Get the number of edges in the graph.

        Returns:
            Number of edges
        """
        return sum(len(edges) for edges in self.adjacency.values())

    def get_all_node_ids(self) -> list[str]:
        """
        Get all node IDs in the graph.

        Returns:
            List of all node IDs
        """
        return list(self.nodes.keys())

    # ============ Persistence ============

    def store(self, dir_path: str) -> dict[str, Any]:
        """
        Save graph to disk.

        Args:
            dir_path: Directory to save to

        Returns:
            Storage metadata
        """
        directory = Path(dir_path)
        directory.mkdir(parents=True, exist_ok=True)

        # Save nodes
        nodes_file = directory / "nodes.json"
        with open(nodes_file, "w", encoding="utf-8") as f:
            json.dump(self.nodes, f, indent=2, ensure_ascii=False)

        # Save edges (adjacency list with relation info)
        # Convert tuples to lists for JSON serialization
        edges_data = {
            node_id: [[n, w, r] for n, w, r in neighbors]
            for node_id, neighbors in self.adjacency.items()
        }
        edges_file = directory / "edges.json"
        with open(edges_file, "w", encoding="utf-8") as f:
            json.dump(edges_data, f, indent=2, ensure_ascii=False)

        # Save config
        config_file = directory / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"name": self.name, "config": self.config}, f, indent=2)

        return {
            "name": self.name,
            "nodes_file": str(nodes_file),
            "edges_file": str(edges_file),
            "node_count": self.node_count(),
            "edge_count": self.edge_count(),
        }

    @classmethod
    def load(cls, name: str, dir_path: str) -> "SimpleGraphIndex":
        """
        Load graph from disk.

        Args:
            name: Index name
            dir_path: Directory to load from

        Returns:
            Loaded graph index
        """
        directory = Path(dir_path)

        # Load config if exists
        config: dict[str, Any] = {}
        config_file = directory / "config.json"
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                saved = json.load(f)
                name = saved.get("name", name)
                config = saved.get("config", {})

        index = cls(name, config)

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

            # Initialize adjacency lists for all nodes
            for node_id in index.nodes:
                index.adjacency[node_id] = []
                index.reverse_adjacency[node_id] = []

            # Reconstruct adjacency lists with relation info
            for from_node, neighbors in edges_data.items():
                # Handle both old format (tuple of 2) and new format (tuple of 3)
                converted_neighbors = []
                for edge in neighbors:
                    if len(edge) == 2:
                        # Old format: [to_node, weight]
                        converted_neighbors.append((edge[0], edge[1], None))
                    else:
                        # New format: [to_node, weight, relation]
                        converted_neighbors.append((edge[0], edge[1], edge[2]))

                index.adjacency[from_node] = converted_neighbors

                # Rebuild reverse adjacency
                for to_node, weight, relation in converted_neighbors:
                    if to_node in index.reverse_adjacency:
                        index.reverse_adjacency[to_node].append((from_node, weight, relation))

        return index

    @staticmethod
    def clear(dir_path: str) -> None:
        """
        Clear stored index data.

        Args:
            dir_path: Directory path to clear
        """
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(dir_path)
