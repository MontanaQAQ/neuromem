"""
LinknoteGraphService - 链接笔记图服务

设计特点:
- 双向链接: 笔记之间的引用关系 (A引用B, B被A引用)
- 图遍历: BFS/DFS 查找关联笔记
- 标签系统: 笔记分类和检索

使用场景:
- Obsidian/Notion 风格的知识管理
- 概念关联和思维导图
- 知识网络构建

索引配置:
- Graph 索引: 存储笔记之间的链接关系
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..base_service import BaseMemoryService
from ..registry import MemoryServiceRegistry

if TYPE_CHECKING:
    pass

import logging

logger = logging.getLogger(__name__)


@MemoryServiceRegistry.register("linknote_graph")
class LinknoteGraphService(BaseMemoryService):
    """
    链接笔记图服务

    核心功能:
    - insert(): 插入笔记 + 自动提取链接
    - retrieve(): 查找关联笔记 (BFS/DFS)
    - get_backlinks(): 获取反向链接
    - get_neighbors(): 获取相邻笔记
    """

    def _setup_indexes(self) -> None:
        """配置图索引 + 向量索引（A-Mem 需要）"""
        # 创建无向图索引 (双向链接)
        self.collection.add_index(
            name="note_graph",
            index_type="graph",
            config={"directed": False},  # 无向图: A→B 等价于 B→A
        )

        # 添加向量索引用于语义检索（A-Mem 核心功能）
        embedding_dim = self.config.get("embedding_dim", 1024)
        index_type = self.config.get("index_type", "flat")

        self.collection.add_index(
            name="note_vector",
            index_type="faiss",  # IndexFactory 注册的类型是 "faiss" 而非 "vector"
            config={
                "dim": embedding_dim,
                "index_type": index_type,
            },
        )

        logger.info(
            f"LinknoteGraphService: Created graph index + vector index (dim={embedding_dim}, type={index_type})"
        )

    def insert(
        self,
        entry: str,
        vector: Any = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: str = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """
        插入笔记（统一接口）

        Args:
            entry: 笔记内容
            vector: 向量（可选，用于语义检索）
            metadata: 元数据 (可包含 tags, title 等)
            insert_mode: 插入模式（passive/active）
            insert_params: 插入参数
                - links: List[str] 明确指定的链接 (其他笔记ID)

        Returns:
            data_id: 笔记 ID

        Example:
            # 插入新笔记并链接到已有笔记
            note_id = service.insert(
                entry="Python 是一门编程语言",
                vector=[0.1, 0.2, ...],  # BGE-M3 embedding
                metadata={"title": "Python", "tags": ["programming"]},
                insert_params={"links": ["note_1", "note_2"]}
            )
        """
        # 1. 生成 data_id 并直接存储数据
        import time

        data_id = self.collection._generate_id(entry, metadata)
        self.collection.raw_data[data_id] = {
            "text": entry,
            "metadata": metadata or {},
            "created_at": time.time(),
        }

        # 2. 手动添加节点到图索引
        graph_index = self.collection.indexes.get("note_graph")
        if graph_index:
            node_data = {"text": entry, "metadata": metadata or {}}
            graph_index.add(data_id, node_data)

        # 3. 添加向量到向量索引（A-Mem 核心）
        if vector is not None:
            vector_index = self.collection.indexes.get("note_vector")
            if vector_index:
                # FAISSIndex.add(data_id, text, metadata) - vector 放在 metadata 中
                metadata_with_vector = (metadata or {}).copy()
                metadata_with_vector["vector"] = vector
                vector_index.add(data_id, entry, metadata_with_vector)

        # 4. 提取链接关系
        insert_params = insert_params or {}
        links = insert_params.get("links", [])
        if links:
            self._add_links(data_id, links)

        logger.debug(
            f"Inserted note {data_id[:8]}... with {len(links)} links, vector={'yes' if vector is not None else 'no'}"
        )
        return data_id

    def retrieve(
        self,
        query: str | None = None,
        vector: Any = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 5,
        hints: dict[str, Any] | None = None,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        检索关联笔记（支持向量检索 + 图遍历）

        Args:
            query: 查询文本（如果没有 vector，用于图遍历起始节点ID）
            vector: 查询向量（A-Mem 模式：使用向量相似度检索）
            metadata: 元数据过滤条件（可选）
            top_k: 返回结果数量（默认5）
            hints: 检索策略提示（可选）
            threshold: 相似度阈值（可选）
            **kwargs: 额外参数
                - method: "bfs"或"dfs"(默认BFS，仅图遍历模式)
                - max_hops: 最大跳数(默认2，仅图遍历模式)
                - include_start: 是否包含起始节点(默认False，仅图遍历模式)

        Returns:
            笔记列表: [{"id": "...", "text": "...", "metadata": {...}, "score": 0.9}, ...]

        Example:
            # A-Mem 模式：向量相似度检索
            related = service.retrieve(
                query="Python programming",
                vector=[0.1, 0.2, ...],  # 查询向量
                top_k=10
            )

            # 图遍历模式：查找与note_1相关的所有笔记(2跳内)
            related = service.retrieve(
                query="note_1",
                top_k=10,
                method="bfs",
                max_hops=2
            )
        """
        # A-Mem 模式：如果提供了向量，使用向量检索
        if vector is not None:
            vector_index = self.collection.indexes.get("note_vector")
            if vector_index:
                # 向量相似度检索
                result_ids = self.collection.query_by_index(
                    index_name="note_vector",
                    query=vector,
                    top_k=top_k,
                )

                # 获取完整数据并添加score
                results = []
                for data_id in result_ids[:top_k]:
                    data = self.collection.get(data_id)
                    if data:
                        data["id"] = data_id
                        data["score"] = 1.0  # TODO: 实际相似度分数
                        results.append(data)

                logger.debug(f"Vector retrieval: {len(results)} notes")
                return results

        # 图遍历模式：使用起始节点ID进行BFS/DFS
        start_id = query or ""
        method = kwargs.get("method", "bfs")
        max_hops = kwargs.get("max_hops", 2)
        include_start = kwargs.get("include_start", False)

        # 使用图索引的 query 方法进行遍历
        result_ids = self.collection.query_by_index(
            index_name="note_graph",
            query=start_id,
            method=method,
            max_depth=max_hops,
            include_start=include_start,
            top_k=top_k,
        )

        # 获取完整数据
        results = []
        for data_id in result_ids[:top_k]:
            data = self.collection.get(data_id)
            if data:
                # 添加 ID 和距离信息
                data["id"] = data_id
                data["distance"] = 1  # TODO: 实际距离需要图遍历返回
                results.append(data)

        logger.debug(f"Graph traversal: {len(results)} related notes from {start_id[:8]}...")
        return results

    def get_backlinks(self, note_id: str) -> list[str]:
        """
        获取反向链接 (引用了该笔记的其他笔记)

        Args:
            note_id: 笔记 ID

        Returns:
            引用该笔记的笔记 ID 列表

        Note:
            - 在无向图中，neighbors 包含了所有相邻节点
            - 在有向图中，需要区分 in_edges 和 out_edges
        """
        # 获取图索引
        graph_index = self.collection.indexes.get("note_graph")
        if not graph_index:
            return []

        # 获取邻居节点 (无向图中即为所有相关笔记)，不包含自己
        neighbors = graph_index.query(note_id, hop=1, include_start=False)
        return neighbors

    def get_neighbors(self, note_id: str, max_hops: int = 1) -> list[str]:
        """
        获取 N 跳邻居

        Args:
            note_id: 笔记 ID
            max_hops: 最大跳数

        Returns:
            邻居笔记 ID 列表

        Example:
            # 获取直接相连的笔记
            neighbors_1hop = service.get_neighbors("note_1", max_hops=1)

            # 获取2跳内的所有笔记
            neighbors_2hop = service.get_neighbors("note_1", max_hops=2)
        """
        return self.collection.query_by_index(
            index_name="note_graph",
            query=note_id,
            method="bfs",
            max_depth=max_hops,
            include_start=False,
        )

    def _add_links(self, source_id: str, target_ids: list[str]) -> None:
        """
        添加链接关系 (内部方法)

        Args:
            source_id: 源笔记 ID
            target_ids: 目标笔记 ID 列表
        """
        graph_index = self.collection.indexes.get("note_graph")
        if not graph_index:
            logger.warning("Graph index not found")
            return

        for target_id in target_ids:
            # 检查目标笔记是否存在
            if self.collection.get(target_id):
                # 确保目标节点在图中
                if target_id not in graph_index.graph:
                    target_data = self.collection.get(target_id)
                    graph_index.add(target_id, target_data)

                # 添加边 (无向图会自动创建双向边)
                graph_index.graph.add_edge(source_id, target_id, weight=1.0)
                logger.debug(f"Added link: {source_id[:8]}... -> {target_id[:8]}...")
            else:
                logger.warning(f"Target note {target_id} not found, skipping link")
