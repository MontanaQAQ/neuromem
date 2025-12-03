"""
Graph-based memory collection implementation.

Provides graph-based memory storage with nodes and weighted edges.
Designed for knowledge graph RAG and relationship-based retrieval.

设计原则：
- 数据只存一份：text_storage + metadata_storage
- 索引可以有多个：支持多个独立的图索引
- 索引可以独立增删：从某个索引移除不影响数据
"""

from __future__ import annotations

import json
import logging
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import numpy as np

from ..search_engine.graph_index import SimpleGraphIndex
from ..utils.path_utils import get_default_data_dir
from .base_collection import BaseMemoryCollection, IndexType


class GraphMemoryCollection(BaseMemoryCollection):
    """
    Graph-based memory collection.

    Stores documents with graph relationships for knowledge graph RAG.
    Combines text/metadata storage with graph structure.

    设计原则：
    - 数据存储在 text_storage + metadata_storage
    - 图结构存储在 indexes（支持多个图索引）
    - 每个节点的 ID 对应 text_storage 中的 stable_id
    """

    # 声明支持的索引类型
    supported_index_types: ClassVar[set[IndexType]] = {IndexType.GRAPH}

    def __init__(self, config: dict[str, Any]):
        """
        Initialize graph memory collection.

        Args:
            config: 配置字典，必须包含 "name" 字段
        """
        # 调用父类初始化
        super().__init__(config)

        self.indexes: dict[str, SimpleGraphIndex] = {}
        self.logger = logging.getLogger(__name__)
        self.description = config.get("description", "")

    # ==================== 索引管理方法 ====================

    def create_index(
        self,
        config: dict[str, Any],
        index_type: IndexType | None = None,  # 基础 Collection 可忽略
    ) -> bool:
        """
        Create a new graph index.

        Args:
            config: Index configuration with 'name' key
            index_type: 索引类型（GraphMemoryCollection 只支持 GRAPH，此参数可忽略）

        Returns:
            是否创建成功
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
            是否删除成功
        """
        if index_name not in self.indexes:
            self.logger.warning(f"Index '{index_name}' does not exist")
            return False

        del self.indexes[index_name]
        self.logger.info(f"Deleted graph index: {index_name}")
        return True

    def list_indexes(self) -> list[dict[str, Any]]:
        """
        列出所有索引。

        Returns:
            索引信息列表: [{"name": ..., "type": IndexType.GRAPH, "config": {...}}, ...]
        """
        return [
            {
                "name": name,
                "type": IndexType.GRAPH,
                "config": {
                    "node_count": len(index.nodes) if hasattr(index, "nodes") else 0,
                },
            }
            for name, index in self.indexes.items()
        ]

    # ==================== 数据操作方法 ====================

    def insert(
        self,
        content: str,
        index_names: list[str] | str | None = None,
        vector: np.ndarray | None = None,  # 不使用，保持接口一致性
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        插入节点数据。

        Args:
            content: 文本内容
            index_names: 目标索引名列表或单个索引名（None 表示只存数据不建索引）
            vector: 向量（Graph 索引不使用此参数）
            metadata: 元数据
            **kwargs: 其他参数，支持:
                - node_id: 指定节点 ID（否则自动生成）
                - edges: [(target_id, weight), ...] 同时创建的边

        Returns:
            stable_id (节点 ID)
        """
        # 获取或生成节点 ID
        node_id = kwargs.get("node_id")
        if node_id is None:
            node_id = self._get_stable_id(content, metadata)

        # 存储文本
        self.text_storage.store(node_id, content)

        # 存储元数据
        if metadata:
            for field in metadata:
                if not self.metadata_storage.has_field(field):
                    self.metadata_storage.add_field(field)
            self.metadata_storage.store(node_id, metadata)

        # 规范化 index_names
        target_indexes: list[str] = []
        if index_names is None:
            pass  # 只存数据，不建索引
        elif isinstance(index_names, str):
            target_indexes = [index_names]
        else:
            target_indexes = list(index_names)

        # 添加到各图索引
        for idx_name in target_indexes:
            if idx_name not in self.indexes:
                self.create_index({"name": idx_name})
            self.indexes[idx_name].add_node(node_id, content)

        # 处理边
        edges = kwargs.get("edges", [])
        for target_id, weight in edges:
            for idx_name in target_indexes:
                self.indexes[idx_name].add_edge(node_id, target_id, weight)

        return node_id

    def insert_to_index(
        self,
        item_id: str,
        index_name: str,
        vector: np.ndarray | None = None,  # 不使用，保持接口一致性
        **kwargs: Any,
    ) -> bool:
        """
        将已有数据加入索引（用于跨索引迁移）。

        Args:
            item_id: 数据 ID
            index_name: 目标索引名
            vector: 向量（Graph 索引不使用此参数）

        Returns:
            成功/失败
        """
        # 获取文本内容
        content = self.text_storage.get(item_id)
        if content is None:
            self.logger.warning(f"Item '{item_id}' not found in storage.")
            return False

        # 确保索引存在
        if index_name not in self.indexes:
            self.create_index({"name": index_name})

        # 添加节点
        self.indexes[index_name].add_node(item_id, content)
        return True

    def remove_from_index(self, item_id: str, index_name: str) -> bool:
        """
        从索引移除（数据保留）。

        Args:
            item_id: 数据 ID
            index_name: 索引名称

        Returns:
            成功/失败
        """
        if index_name not in self.indexes:
            self.logger.warning(f"Index '{index_name}' does not exist.")
            return False

        index = self.indexes[index_name]
        if not index.has_node(item_id):
            return False

        index.remove_node(item_id)
        return True

    def retrieve(
        self,
        query: str | np.ndarray | None = None,
        index_name: str | None = None,
        top_k: int = 10,
        with_metadata: bool = False,
        metadata_filter: Callable[[dict[str, Any]], bool] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        检索数据（图遍历模式）。

        Args:
            query: 查询（文本或向量 - 用于定位起始节点）
            index_name: 使用的索引名称
            top_k: 返回数量
            with_metadata: 是否返回 metadata
            metadata_filter: 元数据过滤函数
            **kwargs: 图特有参数:
                - start_node: 起始节点 ID（直接指定起始点）
                - max_depth: 最大遍历深度（默认 2）
                - direction: "outgoing" | "incoming" | "both"

        Returns:
            检索结果列表: [{"id": ..., "text": ..., "metadata": ..., "depth": ...}, ...]
        """
        if index_name is None:
            index_name = "default"

        if index_name not in self.indexes:
            self.logger.warning(f"Index '{index_name}' does not exist.")
            return []

        index = self.indexes[index_name]

        # 获取起始节点
        start_node = kwargs.get("start_node")
        max_depth = kwargs.get("max_depth", 2)

        if start_node is None:
            # 如果没有指定起始节点，尝试根据 query 找到匹配的节点
            if query is None:
                self.logger.warning("No start_node or query provided for graph retrieval.")
                return []

            # 简单的文本匹配查找起始节点
            if isinstance(query, str):
                for node_id in self.text_storage.get_all_ids():
                    text = self.text_storage.get(node_id)
                    if text and query.lower() in text.lower():
                        start_node = node_id
                        break

            if start_node is None:
                self.logger.warning(f"No matching node found for query: {query}")
                return []

        if not index.has_node(start_node):
            self.logger.warning(f"Start node '{start_node}' not found in index.")
            return []

        # BFS 遍历
        visited: set[str] = set()
        results: list[dict[str, Any]] = []
        queue: deque[tuple[str, int]] = deque([(start_node, 0)])

        while queue and len(results) < top_k:
            node_id, depth = queue.popleft()

            if node_id in visited or depth > max_depth:
                continue

            visited.add(node_id)

            # 应用元数据过滤
            if metadata_filter:
                node_metadata = self.metadata_storage.get(node_id) or {}
                if not metadata_filter(node_metadata):
                    continue

            result: dict[str, Any] = {
                "id": node_id,
                "text": self.text_storage.get(node_id),
                "depth": depth,
                "score": 1.0 / (depth + 1),  # 深度越浅，分数越高
            }
            if with_metadata:
                result["metadata"] = self.metadata_storage.get(node_id)

            results.append(result)

            if depth < max_depth:
                neighbors = index.get_neighbors(node_id, k=100)
                for neighbor_id, _ in neighbors:
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, depth + 1))

        return results

    def delete(self, item_id: str) -> bool:
        """
        完全删除节点（数据 + 所有索引）。

        Args:
            item_id: 节点 ID

        Returns:
            是否删除成功
        """
        if not self.text_storage.has(item_id):
            self.logger.warning(f"Item '{item_id}' not found.")
            return False

        # 从存储中删除
        self.text_storage.delete(item_id)
        self.metadata_storage.delete(item_id)

        # 从所有索引中删除
        for index in self.indexes.values():
            if index.has_node(item_id):
                index.remove_node(item_id)

        return True

    def update(
        self,
        item_id: str,
        new_content: str | None = None,
        new_vector: np.ndarray | None = None,  # 不使用，保持接口一致性
        new_metadata: dict[str, Any] | None = None,
        index_name: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        更新节点。

        Args:
            item_id: 节点 ID
            new_content: 新文本内容
            new_vector: 新向量（Graph 索引不使用此参数）
            new_metadata: 新元数据
            index_name: 索引名称（未使用）

        Returns:
            是否更新成功
        """
        if not self.text_storage.has(item_id):
            self.logger.warning(f"Item '{item_id}' not found.")
            return False

        # 更新文本
        if new_content is not None:
            self.text_storage.store(item_id, new_content)
            # 更新所有索引中的节点数据
            for index in self.indexes.values():
                if index.has_node(item_id):
                    index.add_node(item_id, new_content)

        # 更新元数据
        if new_metadata is not None:
            for field in new_metadata:
                if not self.metadata_storage.has_field(field):
                    self.metadata_storage.add_field(field)
            self.metadata_storage.store(item_id, new_metadata)

        return True

    # ==================== 图特有方法 ====================

    def add_node(
        self,
        node_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        index_name: str = "default",
    ) -> str:
        """
        Add a node to the graph (向后兼容方法).

        Args:
            node_id: Unique node identifier
            text: Text content for the node
            metadata: Optional metadata
            index_name: Graph index to add to

        Returns:
            Node ID
        """
        return self.insert(
            content=text,
            index_names=index_name,
            metadata=metadata,
            node_id=node_id,
        )

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        weight: float = 1.0,
        index_name: str = "default",
    ) -> bool:
        """
        Add an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            weight: Edge weight
            index_name: Graph index to add to

        Returns:
            是否成功
        """
        if index_name not in self.indexes:
            self.create_index({"name": index_name})

        self.indexes[index_name].add_edge(from_node, to_node, weight)
        return True

    def remove_edge(
        self,
        from_node: str,
        to_node: str,
        index_name: str = "default",
    ) -> bool:
        """
        Remove an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            index_name: Graph index

        Returns:
            是否成功
        """
        if index_name not in self.indexes:
            return False

        self.indexes[index_name].remove_edge(from_node, to_node)
        return True

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
            List of neighbor dicts with 'node_id', 'weight', and 'data'
        """
        if index_name not in self.indexes:
            return []

        neighbors = self.indexes[index_name].get_neighbors(node_id, k)
        return [
            {
                "node_id": nid,
                "weight": weight,
                "data": self.indexes[index_name].get_node_data(nid),
            }
            for nid, weight in neighbors
        ]

    def retrieve_by_graph(
        self,
        start_node: str,
        max_depth: int = 2,
        max_nodes: int = 10,
        index_name: str = "default",
    ) -> list[dict[str, Any]]:
        """
        Retrieve nodes via BFS graph traversal (向后兼容方法).

        Args:
            start_node: Starting node ID
            max_depth: Maximum traversal depth
            max_nodes: Maximum nodes to return
            index_name: Graph index to traverse

        Returns:
            List of node dicts with 'node_id', 'data', 'depth'
        """
        results = self.retrieve(
            query=None,
            index_name=index_name,
            top_k=max_nodes,
            with_metadata=False,
            start_node=start_node,
            max_depth=max_depth,
        )
        # 转换为旧格式
        return [
            {"node_id": r["id"], "data": r["text"], "depth": r.get("depth", 0)} for r in results
        ]

    # ==================== 持久化方法 ====================

    def store(self, path: str | None = None) -> dict[str, Any]:
        """
        Save collection to disk.

        Args:
            path: Optional data directory

        Returns:
            Storage metadata
        """
        if path is None:
            path = get_default_data_dir()

        collection_path = Path(path) / "graph_collection" / self.name
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

        # Store metadata
        metadata_ids = self.get_all_ids()
        metadata_data = {"store": {mid: self.metadata_storage.get(mid) for mid in metadata_ids}}
        with open(collection_path / "metadata_storage.json", "w", encoding="utf-8") as f:
            json.dump(metadata_data, f, indent=2)

        # Store graph indexes
        indexes_dir = collection_path / "indexes"
        indexes_dir.mkdir(parents=True, exist_ok=True)

        for index_name, index in self.indexes.items():
            index_dir = indexes_dir / index_name
            index.store(str(index_dir))

        return {
            "collection_path": str(collection_path),
            "node_count": len(self.get_all_ids()),
            "index_count": len(self.indexes),
        }

    @classmethod
    def load(cls, name: str, path: str | None = None) -> GraphMemoryCollection:
        """
        Load collection from disk.

        Args:
            name: Collection name
            path: Data directory (can be base dir or collection dir)

        Returns:
            Loaded collection
        """
        if path is None:
            path = get_default_data_dir()

        # Handle both full path and base path
        collection_path = Path(path)
        if not (collection_path / "config.json").exists():
            # path is base directory, append collection path
            collection_path = collection_path / "graph_collection" / name

        # Load config first
        config_file = collection_path / "config.json"
        config: dict[str, Any] = {"name": name}
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                loaded_config = json.load(f)
                config["description"] = loaded_config.get("description", "")

        # Create collection with config
        collection = cls(config)

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
            if "store" in metadata_data:
                for meta_id, meta in metadata_data["store"].items():
                    for field in meta:
                        if not collection.metadata_storage.has_field(field):
                            collection.metadata_storage.add_field(field)
                    collection.metadata_storage.store(meta_id, meta)

        # Load graph indexes
        indexes_dir = collection_path / "indexes"
        if indexes_dir.exists():
            for index_dir in indexes_dir.iterdir():
                if index_dir.is_dir():
                    index_name = index_dir.name
                    collection.indexes[index_name] = SimpleGraphIndex.load(
                        index_name, str(index_dir)
                    )

        return collection
