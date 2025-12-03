"""
Hybrid Memory Collection - 混合索引 Collection

设计原则：
- Collection = 一份数据 (text_storage + metadata_storage) + 多种类型的索引
- 数据只存一份，索引可以有多个
- 支持在同一份数据上建立 VDB、KV、Graph 三种类型的索引
- 索引可以独立增删：insert_to_index / remove_from_index

MemoryOS 示例场景：
1. 新记忆插入 → 进入 FIFO 队列（KV索引：按时间排序）
2. FIFO 满了 → Service 决定：
   - 从 FIFO 索引删除 (remove_from_index)
   - 数据保留，加入 Segment 索引 (insert_to_index)
3. 检索时：
   - 最近记忆 → 查 FIFO 索引
   - 语义相关 → 查 Segment 索引

核心方法：
- insert(content, index_names=[...]) - 存数据 + 加入多个索引
- insert_to_index(item_id, index_name) - 将已有数据加到索引
- remove_from_index(item_id, index_name) - 从索引移除（数据保留）
- delete(item_id) - 完全删除（数据 + 所有索引）
- retrieve(query, index_name) - 从指定索引检索
- retrieve_multi(queries, fusion_strategy) - 多索引检索 + 融合
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, ClassVar

import numpy as np

from ..search_engine import (
    BaseGraphIndex,
    BaseKVIndex,
    BaseVDBIndex,
    IndexFactory,
)
from ..utils.path_utils import get_default_data_dir
from .base_collection import BaseMemoryCollection, IndexType


class HybridCollection(BaseMemoryCollection):
    """
    混合索引 Collection - 在同一份数据上支持创建多种类型的索引。

    支持的索引类型：
    - VDB 索引（向量检索）: FAISS 等
    - KV 索引（文本检索）: BM25, FIFO, 排序等
    - Graph 索引（关系图）: 邻接表, PPR 等

    数据只存一份 (text_storage + metadata_storage)，索引可以有多个。
    """

    # 支持所有索引类型
    supported_index_types: ClassVar[set[IndexType]] = {
        IndexType.VDB,
        IndexType.KV,
        IndexType.GRAPH,
    }

    def __init__(self, config: dict[str, Any]):
        """
        初始化 HybridCollection。

        Args:
            config: 配置字典
                - name: Collection 名称（必须）
                - rrf_k: RRF 融合参数（默认 60）
        """
        super().__init__(config)

        self.logger = logging.getLogger(__name__)

        # RRF 融合参数
        self.rrf_k = config.get("rrf_k", 60)

        # 多种类型的索引（在同一份数据上）
        self.vdb_indexes: dict[str, BaseVDBIndex] = {}  # VDB 向量索引
        self.kv_indexes: dict[str, BaseKVIndex] = {}  # KV 文本索引
        self.graph_indexes: dict[str, BaseGraphIndex] = {}  # Graph 图索引

        # 索引元信息: name -> {type: IndexType, config: {...}, created_time: ...}
        self.index_meta: dict[str, dict[str, Any]] = {}

        self.logger.info(f"HybridCollection '{self.name}' initialized")

    # ==================== 索引管理方法 ====================

    def create_index(
        self,
        config: dict[str, Any],
        index_type: IndexType | None = None,
    ) -> bool:
        """
        创建索引（支持多种类型）。

        Args:
            config: 索引配置
                - name: 索引名称（必须）
                - type: 索引类型 "vdb" | "kv" | "graph"（可选，默认 vdb）

                VDB 类型额外参数：
                    - dim: 向量维度（必须）
                    - backend_type: 后端类型 "FAISS" | "LSH" 等

                KV 类型额外参数：
                    - index_type: "bm25s" | "bm25" 等

                Graph 类型额外参数：
                    - index_type: "simple" | "adjacency" 等

            index_type: 索引类型（优先于 config["type"]）

        Returns:
            是否创建成功
        """
        index_name = config.get("name")
        if not index_name:
            self.logger.warning("Index name is required")
            return False

        if index_name in self.index_meta:
            self.logger.warning(f"Index '{index_name}' already exists")
            return False

        # 确定索引类型
        type_str = config.get("type", "vdb").lower()
        if index_type is not None:
            type_str = index_type.value

        try:
            if type_str == IndexType.VDB.value or type_str == "vdb":
                return self._create_vdb_index(index_name, config)
            elif type_str == IndexType.KV.value or type_str == "kv":
                return self._create_kv_index(index_name, config)
            elif type_str == IndexType.GRAPH.value or type_str == "graph":
                return self._create_graph_index(index_name, config)
            else:
                self.logger.warning(f"Unknown index type: {type_str}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to create index '{index_name}': {e}")
            return False

    def _create_vdb_index(self, index_name: str, config: dict[str, Any]) -> bool:
        """创建 VDB 索引。"""
        dim = config.get("dim")
        if not isinstance(dim, int) or dim <= 0:
            self.logger.warning("VDB index requires valid 'dim' (positive int)")
            return False

        backend_type = config.get("backend_type", "FAISS")
        index_config = {
            "name": index_name,
            "dim": dim,
            "backend_type": backend_type,
            "config": config.get("index_parameter"),
        }

        index = IndexFactory.create_vdb_index(index_config)
        self.vdb_indexes[index_name] = index

        self.index_meta[index_name] = {
            "type": IndexType.VDB,
            "config": config,
            "created_time": time.time(),
        }

        self.logger.info(f"Created VDB index: {index_name} (dim={dim}, backend={backend_type})")
        return True

    def _create_kv_index(self, index_name: str, config: dict[str, Any]) -> bool:
        """创建 KV 索引。"""
        kv_type = config.get("index_type", "bm25s")
        index_config = {
            "name": index_name,
            "index_type": kv_type,
        }

        index = IndexFactory.create_kv_index(index_config)
        self.kv_indexes[index_name] = index

        self.index_meta[index_name] = {
            "type": IndexType.KV,
            "config": config,
            "created_time": time.time(),
        }

        self.logger.info(f"Created KV index: {index_name} (type={kv_type})")
        return True

    def _create_graph_index(self, index_name: str, config: dict[str, Any]) -> bool:
        """创建 Graph 索引。"""
        graph_type = config.get("index_type", "simple")
        index_config = {
            "name": index_name,
            "index_type": graph_type,
        }

        index = IndexFactory.create_graph_index(index_config)
        self.graph_indexes[index_name] = index

        self.index_meta[index_name] = {
            "type": IndexType.GRAPH,
            "config": config,
            "created_time": time.time(),
        }

        self.logger.info(f"Created Graph index: {index_name} (type={graph_type})")
        return True

    def delete_index(self, index_name: str) -> bool:
        """
        删除索引。

        Args:
            index_name: 索引名称

        Returns:
            是否删除成功
        """
        if index_name not in self.index_meta:
            self.logger.warning(f"Index '{index_name}' does not exist")
            return False

        idx_type = self.index_meta[index_name]["type"]

        if idx_type == IndexType.VDB:
            del self.vdb_indexes[index_name]
        elif idx_type == IndexType.KV:
            del self.kv_indexes[index_name]
        elif idx_type == IndexType.GRAPH:
            del self.graph_indexes[index_name]

        del self.index_meta[index_name]
        self.logger.info(f"Deleted index: {index_name}")
        return True

    def list_indexes(self) -> list[dict[str, Any]]:
        """
        列出所有索引。

        Returns:
            索引信息列表: [{"name": ..., "type": IndexType, "config": {...}}, ...]
        """
        return [
            {
                "name": name,
                "type": meta["type"],
                "config": meta.get("config", {}),
            }
            for name, meta in self.index_meta.items()
        ]

    def get_index_type(self, index_name: str) -> IndexType | None:
        """获取索引类型。"""
        meta = self.index_meta.get(index_name)
        return meta["type"] if meta else None

    def get_index_count(self, index_name: str) -> int:
        """
        获取索引中的元素数量。

        Args:
            index_name: 索引名称

        Returns:
            元素数量
        """
        if index_name not in self.index_meta:
            return 0

        idx_type = self.index_meta[index_name]["type"]

        if idx_type == IndexType.VDB and index_name in self.vdb_indexes:
            index = self.vdb_indexes[index_name]
            return index.count() if hasattr(index, "count") else 0
        elif idx_type == IndexType.KV and index_name in self.kv_indexes:
            index = self.kv_indexes[index_name]
            return index.count() if hasattr(index, "count") else 0
        elif idx_type == IndexType.GRAPH and index_name in self.graph_indexes:
            index = self.graph_indexes[index_name]
            return index.node_count() if hasattr(index, "node_count") else len(index.nodes)

        return 0

    # ==================== 数据操作方法 ====================

    def insert(
        self,
        content: str,
        index_names: list[str] | str | None = None,
        vector: np.ndarray | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        插入数据。

        Args:
            content: 文本内容
            index_names: 目标索引名列表或单个索引名（None 表示只存数据不建索引）
            vector: 向量（VDB 索引需要）
            metadata: 元数据
            **kwargs: 额外参数
                - vectors: {index_name: vector} 不同索引使用不同向量
                - edges: [(target_id, weight, relation_type)] 图索引的边

        Returns:
            stable_id
        """
        # 1. 存储数据
        stable_id = self._get_stable_id(content, metadata)
        self.text_storage.store(stable_id, content)

        if metadata:
            for field in metadata:
                if not self.metadata_storage.has_field(field):
                    self.metadata_storage.add_field(field)
            self.metadata_storage.store(stable_id, metadata)

        # 2. 如果没有指定索引，只存数据
        if index_names is None:
            return stable_id

        # 规范化 index_names
        target_indexes: list[str]
        target_indexes = [index_names] if isinstance(index_names, str) else list(index_names)

        # 3. 更新索引
        vectors_map = kwargs.get("vectors", {})
        edges = kwargs.get("edges", [])

        for idx_name in target_indexes:
            if idx_name not in self.index_meta:
                self.logger.warning(f"Index '{idx_name}' not found, skipping")
                continue

            idx_type = self.index_meta[idx_name]["type"]

            if idx_type == IndexType.VDB:
                vec = vectors_map.get(idx_name, vector)
                if vec is not None:
                    self._insert_to_vdb_index(idx_name, stable_id, vec)
                else:
                    self.logger.warning(f"VDB index '{idx_name}' requires vector, skipping")

            elif idx_type == IndexType.KV:
                self._insert_to_kv_index(idx_name, stable_id, content)

            elif idx_type == IndexType.GRAPH:
                self._insert_to_graph_index(idx_name, stable_id, content, edges)

        return stable_id

    def _insert_to_vdb_index(self, index_name: str, item_id: str, vector: np.ndarray) -> bool:
        """插入到 VDB 索引。"""
        if index_name not in self.vdb_indexes:
            return False

        # 处理向量
        processed_vector = self._process_vector(vector)
        if processed_vector is None:
            return False

        # 检查维度
        expected_dim = self.index_meta[index_name]["config"].get("dim")
        if expected_dim and processed_vector.shape[-1] != expected_dim:
            self.logger.warning(
                f"Vector dimension {processed_vector.shape[-1]} != expected {expected_dim}"
            )
            return False

        self.vdb_indexes[index_name].insert(processed_vector, item_id)
        return True

    def _insert_to_kv_index(self, index_name: str, item_id: str, content: str) -> bool:
        """插入到 KV 索引。"""
        if index_name not in self.kv_indexes:
            return False

        self.kv_indexes[index_name].insert(content, item_id)
        return True

    def _insert_to_graph_index(
        self,
        index_name: str,
        item_id: str,
        content: str,
        edges: list[tuple[str, float, ...]] | None = None,
    ) -> bool:
        """插入到 Graph 索引。"""
        if index_name not in self.graph_indexes:
            return False

        graph = self.graph_indexes[index_name]
        graph.add_node(item_id, content)

        # 处理边
        if edges:
            for edge in edges:
                target_id = edge[0]
                weight = edge[1] if len(edge) > 1 else 1.0
                relation = edge[2] if len(edge) > 2 else None
                graph.add_edge(item_id, target_id, weight, relation)

        return True

    def _process_vector(self, vector: np.ndarray | Any) -> np.ndarray | None:
        """处理和归一化向量。"""
        try:
            processed_vector: np.ndarray
            if hasattr(vector, "detach") and hasattr(vector, "cpu"):
                processed_vector = vector.detach().cpu().numpy()
            elif isinstance(vector, list) or not isinstance(vector, np.ndarray):
                processed_vector = np.array(vector)
            else:
                processed_vector = vector
            processed_vector = processed_vector.astype(np.float32)

            # L2 normalization
            norm = np.linalg.norm(processed_vector)
            if norm > 0:
                processed_vector = processed_vector / norm
            return processed_vector
        except Exception as e:
            self.logger.error(f"Failed to process vector: {e}")
            return None

    def insert_to_index(
        self,
        item_id: str,
        index_name: str,
        vector: np.ndarray | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        将已有数据加入索引（用于跨索引迁移）。

        用途：数据已经存在，只需要加到新索引中。
        例如 MemoryOS 场景：从 FIFO 移除后，加入 Segment 索引。

        Args:
            item_id: 数据 ID
            index_name: 目标索引名
            vector: 向量（VDB 索引需要）
            **kwargs: 额外参数
                - edges: 图索引的边

        Returns:
            成功/失败
        """
        if not self.text_storage.has(item_id):
            self.logger.warning(f"Item '{item_id}' not found in storage")
            return False

        if index_name not in self.index_meta:
            self.logger.warning(f"Index '{index_name}' not found")
            return False

        content = self.text_storage.get(item_id)
        idx_type = self.index_meta[index_name]["type"]

        if idx_type == IndexType.VDB:
            if vector is None:
                self.logger.warning("Vector required for VDB index")
                return False
            return self._insert_to_vdb_index(index_name, item_id, vector)

        elif idx_type == IndexType.KV:
            return self._insert_to_kv_index(index_name, item_id, content)

        elif idx_type == IndexType.GRAPH:
            edges = kwargs.get("edges", [])
            return self._insert_to_graph_index(index_name, item_id, content, edges)

        return False

    def remove_from_index(self, item_id: str, index_name: str) -> bool:
        """
        从索引移除（数据保留）。

        用于 MemoryOS 场景：从 FIFO 删除，但保留数据可以加入其他索引。

        Args:
            item_id: 数据 ID
            index_name: 索引名称

        Returns:
            成功/失败
        """
        if index_name not in self.index_meta:
            self.logger.warning(f"Index '{index_name}' not found")
            return False

        idx_type = self.index_meta[index_name]["type"]

        try:
            if idx_type == IndexType.VDB and index_name in self.vdb_indexes:
                self.vdb_indexes[index_name].delete(item_id)
                return True

            elif idx_type == IndexType.KV and index_name in self.kv_indexes:
                self.kv_indexes[index_name].delete(item_id)
                return True

            elif idx_type == IndexType.GRAPH and index_name in self.graph_indexes:
                self.graph_indexes[index_name].remove_node(item_id)
                return True

        except Exception as e:
            self.logger.error(f"Failed to remove from index '{index_name}': {e}")
            return False

        return False

    def delete(self, item_id: str) -> bool:
        """
        完全删除数据（从所有索引中移除）。

        Args:
            item_id: 条目 ID

        Returns:
            是否删除成功
        """
        if not self.text_storage.has(item_id):
            self.logger.warning(f"Item '{item_id}' not found")
            return False

        # 从所有 VDB 索引删除
        for _idx_name, index in self.vdb_indexes.items():
            with contextlib.suppress(Exception):
                index.delete(item_id)

        # 从所有 KV 索引删除
        for _idx_name, index in self.kv_indexes.items():
            with contextlib.suppress(Exception):
                index.delete(item_id)

        # 从所有 Graph 索引删除
        for _idx_name, index in self.graph_indexes.items():
            try:
                if hasattr(index, "has_node") and index.has_node(item_id):
                    index.remove_node(item_id)
            except Exception:
                pass

        # 删除存储的数据
        self.text_storage.delete(item_id)
        self.metadata_storage.delete(item_id)

        return True

    def update(
        self,
        item_id: str,
        new_content: str | None = None,
        new_vector: np.ndarray | None = None,
        new_metadata: dict[str, Any] | None = None,
        index_name: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        更新条目。

        Args:
            item_id: 条目 ID
            new_content: 新文本内容
            new_vector: 新向量
            new_metadata: 新元数据
            index_name: 索引名称（未使用）
            **kwargs: 额外参数

        Returns:
            是否更新成功
        """
        if not self.text_storage.has(item_id):
            self.logger.warning(f"Item '{item_id}' not found")
            return False

        # 更新文本
        if new_content is not None:
            self.text_storage.store(item_id, new_content)
            # 更新所有 KV 索引
            for _kv_name, index in self.kv_indexes.items():
                index.delete(item_id)
                index.insert(new_content, item_id)
            # 更新所有 Graph 索引的节点数据
            for _graph_name, index in self.graph_indexes.items():
                if hasattr(index, "has_node") and index.has_node(item_id):
                    index.add_node(item_id, new_content)

        # 更新元数据
        if new_metadata is not None:
            for field in new_metadata:
                if not self.metadata_storage.has_field(field):
                    self.metadata_storage.add_field(field)
            self.metadata_storage.store(item_id, new_metadata)

        # 更新向量（需要指定索引或更新所有 VDB 索引）
        if new_vector is not None:
            processed_vector = self._process_vector(new_vector)
            if processed_vector is not None:
                target_indexes = [index_name] if index_name else list(self.vdb_indexes.keys())
                for idx_name in target_indexes:
                    if idx_name in self.vdb_indexes:
                        self.vdb_indexes[idx_name].delete(item_id)
                        self._insert_to_vdb_index(idx_name, item_id, processed_vector)

        return True

    # ==================== 检索方法 ====================

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
        检索数据。

        Args:
            query: 查询（文本或向量）
            index_name: 使用的索引
            top_k: 返回数量
            with_metadata: 是否返回 metadata
            metadata_filter: 元数据过滤函数
            **kwargs: 额外参数
                - threshold: 相似度阈值（VDB）
                - start_node: 图遍历起点（Graph）
                - max_depth: 图遍历深度（Graph）

        Returns:
            检索结果列表: [{"id": ..., "text": ..., "metadata": ..., "score": ...}, ...]
        """
        if index_name is None or index_name not in self.index_meta:
            self.logger.warning(f"Index '{index_name}' not found")
            return []

        idx_type = self.index_meta[index_name]["type"]
        result_ids: list[str] = []
        scores: list[float] = []

        if idx_type == IndexType.VDB:
            result_ids, scores = self._retrieve_from_vdb(
                index_name, query, top_k, kwargs.get("threshold")
            )

        elif idx_type == IndexType.KV:
            result_ids, scores = self._retrieve_from_kv(index_name, query, top_k)

        elif idx_type == IndexType.GRAPH:
            result_ids, scores = self._retrieve_from_graph(
                index_name, query, top_k, kwargs.get("start_node"), kwargs.get("max_depth", 2)
            )

        # 应用元数据过滤
        if metadata_filter:
            filtered_results = []
            filtered_scores = []
            for i, item_id in enumerate(result_ids):
                meta = self.metadata_storage.get(item_id) or {}
                if metadata_filter(meta):
                    filtered_results.append(item_id)
                    filtered_scores.append(scores[i] if i < len(scores) else 0.0)
            result_ids = filtered_results
            scores = filtered_scores

        # 组装结果
        results = []
        for i, item_id in enumerate(result_ids[:top_k]):
            item: dict[str, Any] = {
                "id": item_id,
                "text": self.text_storage.get(item_id),
                "score": scores[i] if i < len(scores) else 0.0,
            }
            if with_metadata:
                item["metadata"] = self.metadata_storage.get(item_id)
            results.append(item)

        return results

    def _retrieve_from_vdb(
        self,
        index_name: str,
        query: str | np.ndarray | None,
        top_k: int,
        threshold: float | None = None,
    ) -> tuple[list[str], list[float]]:
        """从 VDB 索引检索。"""
        if not isinstance(query, np.ndarray):
            self.logger.warning("VDB index requires vector query")
            return [], []

        if index_name not in self.vdb_indexes:
            return [], []

        processed_query = self._process_vector(query)
        if processed_query is None:
            return [], []

        index = self.vdb_indexes[index_name]
        ids, distances = index.search(processed_query, topk=top_k, threshold=threshold)

        # 处理返回格式
        if ids and isinstance(ids[0], (list, np.ndarray)):
            ids = list(ids[0])
        if distances and isinstance(distances[0], (list, np.ndarray)):
            distances = list(distances[0])

        return [str(i) for i in ids], list(distances)

    def _retrieve_from_kv(
        self, index_name: str, query: str | np.ndarray | None, top_k: int
    ) -> tuple[list[str], list[float]]:
        """从 KV 索引检索。"""
        if not isinstance(query, str):
            self.logger.warning("KV index requires text query")
            return [], []

        if index_name not in self.kv_indexes:
            return [], []

        index = self.kv_indexes[index_name]

        # 尝试使用带分数的搜索
        if hasattr(index, "search_with_scores"):
            results = index.search_with_scores(query, topk=top_k)
            ids = [r[0] for r in results]
            scores = [r[1] for r in results]
            return ids, scores
        else:
            ids = index.search(query, topk=top_k)
            return ids, [1.0] * len(ids)

    def _retrieve_from_graph(
        self,
        index_name: str,
        query: str | np.ndarray | None,
        top_k: int,
        start_node: str | None = None,
        max_depth: int = 2,
    ) -> tuple[list[str], list[float]]:
        """从 Graph 索引检索。"""
        if index_name not in self.graph_indexes:
            return [], []

        graph = self.graph_indexes[index_name]

        # 如果没有指定起始节点，尝试根据 query 找匹配的节点
        if start_node is None:
            if query is None or not isinstance(query, str):
                self.logger.warning("Graph retrieval requires start_node or text query")
                return [], []

            # 简单的文本匹配查找起始节点
            for node_id in self.text_storage.get_all_ids():
                text = self.text_storage.get(node_id)
                if text and query.lower() in text.lower():
                    start_node = node_id
                    break

            if start_node is None:
                return [], []

        if not hasattr(graph, "has_node") or not graph.has_node(start_node):
            return [], []

        # BFS 遍历
        from collections import deque

        visited: set[str] = set()
        result_ids: list[str] = []
        scores: list[float] = []
        queue: deque[tuple[str, int]] = deque([(start_node, 0)])

        while queue and len(result_ids) < top_k:
            node_id, depth = queue.popleft()

            if node_id in visited or depth > max_depth:
                continue

            visited.add(node_id)
            result_ids.append(node_id)
            scores.append(1.0 / (depth + 1))  # 深度越浅，分数越高

            if depth < max_depth:
                neighbors = graph.get_neighbors(node_id, k=100)
                for neighbor_id, _ in neighbors:
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, depth + 1))

        return result_ids, scores

    def retrieve_multi(
        self,
        queries: dict[str, Any],
        top_k: int = 10,
        fusion_strategy: str = "rrf",
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        多索引检索 + 融合。

        Args:
            queries: {index_name: query} 每个索引的查询
            top_k: 最终返回数量
            fusion_strategy: "rrf" | "weighted" | "union"
            **kwargs: 额外参数
                - weights: {index_name: weight} 加权融合权重

        Returns:
            融合后的检索结果列表
        """
        all_results: dict[str, list[dict[str, Any]]] = {}

        for index_name, query in queries.items():
            results = self.retrieve(
                query=query,
                index_name=index_name,
                top_k=top_k * 2,  # 多取一些用于融合
                with_metadata=True,
            )
            all_results[index_name] = results

        # 融合
        if fusion_strategy == "rrf":
            return self._rrf_fusion(all_results, top_k)
        elif fusion_strategy == "weighted":
            weights = kwargs.get("weights", {})
            return self._weighted_fusion(all_results, top_k, weights)
        else:  # union
            return self._union_fusion(all_results, top_k)

    def _rrf_fusion(
        self, results_by_index: dict[str, list[dict[str, Any]]], top_k: int
    ) -> list[dict[str, Any]]:
        """Reciprocal Rank Fusion (RRF) 融合。"""
        scores: dict[str, float] = defaultdict(float)
        item_map: dict[str, dict[str, Any]] = {}

        for results in results_by_index.values():
            for rank, item in enumerate(results):
                item_id = item["id"]
                scores[item_id] += 1.0 / (self.rrf_k + rank + 1)
                item_map[item_id] = item

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [
            {**item_map[id_], "fused_score": scores[id_]}
            for id_ in sorted_ids[:top_k]
            if id_ in item_map
        ]

    def _weighted_fusion(
        self,
        results_by_index: dict[str, list[dict[str, Any]]],
        top_k: int,
        weights: dict[str, float],
    ) -> list[dict[str, Any]]:
        """加权融合。"""
        scores: dict[str, float] = defaultdict(float)
        item_map: dict[str, dict[str, Any]] = {}

        for index_name, results in results_by_index.items():
            weight = weights.get(index_name, 1.0)
            for item in results:
                item_id = item["id"]
                item_score = item.get("score", 0.5)
                scores[item_id] += weight * item_score
                item_map[item_id] = item

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [
            {**item_map[id_], "fused_score": scores[id_]}
            for id_ in sorted_ids[:top_k]
            if id_ in item_map
        ]

    def _union_fusion(
        self, results_by_index: dict[str, list[dict[str, Any]]], top_k: int
    ) -> list[dict[str, Any]]:
        """Union 融合（去重合并）。"""
        seen: set[str] = set()
        all_items: list[dict[str, Any]] = []

        for results in results_by_index.values():
            for item in results:
                if item["id"] not in seen:
                    seen.add(item["id"])
                    all_items.append(item)

        return all_items[:top_k]

    # ==================== 持久化方法 ====================

    def store(self, path: str | None = None) -> dict[str, Any]:
        """
        持久化到磁盘。

        Args:
            path: 存储路径（None 使用默认路径）

        Returns:
            存储元信息
        """
        if path is None:
            path = get_default_data_dir()

        collection_dir = os.path.join(path, "hybrid_collection", self.name)
        os.makedirs(collection_dir, exist_ok=True)

        # 存储 text 和 metadata
        text_path = os.path.join(collection_dir, "text_storage.json")
        metadata_path = os.path.join(collection_dir, "metadata_storage.json")
        self.text_storage.store_to_disk(text_path)
        self.metadata_storage.store_to_disk(metadata_path)

        # 存储各类型索引
        indexes_dir = os.path.join(collection_dir, "indexes")
        os.makedirs(indexes_dir, exist_ok=True)

        # VDB 索引
        vdb_dir = os.path.join(indexes_dir, "vdb")
        os.makedirs(vdb_dir, exist_ok=True)
        for idx_name, index in self.vdb_indexes.items():
            idx_path = os.path.join(vdb_dir, idx_name)
            os.makedirs(idx_path, exist_ok=True)
            index.store(idx_path)

        # KV 索引
        kv_dir = os.path.join(indexes_dir, "kv")
        os.makedirs(kv_dir, exist_ok=True)
        for idx_name, index in self.kv_indexes.items():
            idx_path = os.path.join(kv_dir, idx_name)
            os.makedirs(idx_path, exist_ok=True)
            index.store(idx_path)

        # Graph 索引
        graph_dir = os.path.join(indexes_dir, "graph")
        os.makedirs(graph_dir, exist_ok=True)
        for idx_name, index in self.graph_indexes.items():
            idx_path = os.path.join(graph_dir, idx_name)
            os.makedirs(idx_path, exist_ok=True)
            index.store(idx_path)

        # 存储配置
        config = {
            "name": self.name,
            "rrf_k": self.rrf_k,
            "index_meta": {
                name: {
                    "type": meta["type"].value,
                    "config": meta.get("config", {}),
                    "created_time": meta.get("created_time"),
                }
                for name, meta in self.index_meta.items()
            },
        }
        config_path = os.path.join(collection_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Stored HybridCollection to: {collection_dir}")
        return {"collection_path": collection_dir}

    @classmethod
    def load(cls, name: str, path: str | None = None) -> HybridCollection:
        """
        从磁盘加载。

        Args:
            name: Collection 名称
            path: 加载路径（None 使用默认路径）

        Returns:
            加载的 HybridCollection 实例
        """
        if path is None:
            path = os.path.join(get_default_data_dir(), "hybrid_collection", name)
        else:
            path = os.path.join(path, "hybrid_collection", name)

        config_path = os.path.join(path, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No config found for collection at {config_path}")

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # 创建实例
        instance = cls({"name": name, "rrf_k": config.get("rrf_k", 60)})

        # 加载 text 和 metadata
        text_path = os.path.join(path, "text_storage.json")
        metadata_path = os.path.join(path, "metadata_storage.json")
        instance.text_storage.load_from_disk(text_path)
        instance.metadata_storage.load_from_disk(metadata_path)

        # 加载索引
        indexes_dir = os.path.join(path, "indexes")
        index_meta = config.get("index_meta", {})

        for idx_name, meta in index_meta.items():
            idx_type_str = meta.get("type", "vdb")
            idx_type = IndexType(idx_type_str)
            idx_config = meta.get("config", {})

            if idx_type == IndexType.VDB:
                idx_path = os.path.join(indexes_dir, "vdb", idx_name)
                backend_type = idx_config.get("backend_type", "faiss")
                index = IndexFactory.load_vdb_index(idx_name, idx_path, backend_type)
                instance.vdb_indexes[idx_name] = index

            elif idx_type == IndexType.KV:
                idx_path = os.path.join(indexes_dir, "kv", idx_name)
                kv_type = idx_config.get("index_type", "bm25s")
                index = IndexFactory.load_kv_index(idx_name, idx_path, kv_type)
                instance.kv_indexes[idx_name] = index

            elif idx_type == IndexType.GRAPH:
                idx_path = os.path.join(indexes_dir, "graph", idx_name)
                graph_type = idx_config.get("index_type", "simple")
                index = IndexFactory.load_graph_index(idx_name, idx_path, graph_type)
                instance.graph_indexes[idx_name] = index

            instance.index_meta[idx_name] = {
                "type": idx_type,
                "config": idx_config,
                "created_time": meta.get("created_time"),
            }

        instance.logger.info(f"Loaded HybridCollection from: {path}")
        return instance

    # ==================== FIFO 特有方法（MemoryOS 支持）====================

    def get_oldest_items(self, index_name: str, count: int) -> list[str]:
        """
        获取 KV 索引中最旧的 N 个元素。

        用于 MemoryOS：获取要淘汰的元素。

        Args:
            index_name: KV 索引名称
            count: 要获取的数量

        Returns:
            最旧元素的 ID 列表
        """
        if index_name not in self.kv_indexes:
            return []

        index = self.kv_indexes[index_name]
        if hasattr(index, "get_oldest"):
            return index.get_oldest(count)

        # 如果索引不支持 get_oldest，返回空列表
        return []

    def clear(self) -> None:
        """清空所有数据和索引。"""
        # 清空存储
        self.text_storage.clear()
        self.metadata_storage.clear()

        # 清空所有索引
        self.vdb_indexes.clear()
        self.kv_indexes.clear()
        self.graph_indexes.clear()
        self.index_meta.clear()

        self.logger.info(f"HybridCollection '{self.name}' cleared")
