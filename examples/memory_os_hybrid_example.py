#!/usr/bin/env python
"""
MemoryOS 风格的记忆管理示例

演示 HybridCollection 在 MemoryOS 场景中的应用：
- 一份数据 + 多种索引（FIFO + VDB）
- 索引间迁移（从 FIFO 移除，加入 Segment）
- 多路检索（先查 STM，再查 MTM）

核心设计原则：
- Service : Collection = 1 : 1
- Collection = 一份数据 + 多个索引
- 索引可以独立增删

运行方式:
    python examples/memory_os_hybrid_example.py
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    HybridCollection,
)


class MemoryOSService:
    """
    MemoryOS 风格的记忆服务 - 使用 HybridCollection。

    只持有一个 Collection，包含多种索引：
    - stm_fifo: 短期记忆 FIFO 队列 (KV 索引)
    - mtm_segment: 中期记忆语义索引 (VDB 索引)
    - ltm_archive: 长期记忆归档索引 (VDB 索引)
    """

    def __init__(
        self,
        stm_capacity: int = 10,
        mtm_capacity: int = 100,
        embedding_dim: int = 768,
    ):
        """
        初始化 MemoryOS 服务。

        Args:
            stm_capacity: STM 容量限制
            mtm_capacity: MTM 容量限制
            embedding_dim: 向量维度
        """
        self.stm_capacity = stm_capacity
        self.mtm_capacity = mtm_capacity
        self.embedding_dim = embedding_dim

        # 只持有一个 HybridCollection
        self.collection = HybridCollection({"name": "memory_os"})

        # 创建 STM 索引 (FIFO 队列)
        self.collection.create_index(
            {
                "name": "stm_fifo",
                "type": "kv",
                "index_type": "bm25s",
            }
        )

        # 创建 MTM 索引 (VDB 语义检索)
        self.collection.create_index(
            {
                "name": "mtm_segment",
                "type": "vdb",
                "dim": embedding_dim,
                "backend_type": "FAISS",
            }
        )

        # 创建 LTM 索引 (VDB 长期存储)
        self.collection.create_index(
            {
                "name": "ltm_archive",
                "type": "vdb",
                "dim": embedding_dim,
                "backend_type": "FAISS",
            }
        )

        # 跟踪 STM 队列中的 ID（用于 FIFO 淘汰）
        self._stm_queue: list[str] = []

        print("MemoryOS Service initialized with:")
        print(f"  - STM capacity: {stm_capacity}")
        print(f"  - MTM capacity: {mtm_capacity}")
        print(f"  - Embedding dim: {embedding_dim}")

    def insert(
        self,
        content: str,
        vector: np.ndarray,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        插入新记忆。

        流程：
        1. 存数据 + 插入 STM FIFO
        2. 检查 FIFO 是否溢出
        3. 如果溢出，迁移最旧的记忆到 MTM

        Args:
            content: 记忆内容
            vector: 记忆向量
            metadata: 元数据

        Returns:
            记忆 ID
        """
        # 1. 插入到 STM FIFO
        mem_metadata = {
            **(metadata or {}),
            "insert_time": time.time(),
            "tier": "stm",
        }
        item_id = self.collection.insert(
            content=content,
            index_names=["stm_fifo"],
            metadata=mem_metadata,
        )

        # 保存向量用于后续迁移
        self._stm_queue.append((item_id, vector))

        print(f"[INSERT] Added to STM: {item_id[:16]}... (queue size: {len(self._stm_queue)})")

        # 2. 检查 STM 是否溢出
        if len(self._stm_queue) > self.stm_capacity:
            self._migrate_oldest_to_mtm()

        return item_id

    def _migrate_oldest_to_mtm(self) -> None:
        """将最旧的 STM 记忆迁移到 MTM。"""
        if not self._stm_queue:
            return

        # 获取最旧的记忆
        old_id, old_vector = self._stm_queue.pop(0)

        # 从 STM 索引移除
        self.collection.remove_from_index(old_id, "stm_fifo")

        # 加入 MTM 索引
        self.collection.insert_to_index(old_id, "mtm_segment", vector=old_vector)

        # 更新元数据（使用 update 方法确保字段被注册）
        old_meta = self.collection.get_metadata(old_id) or {}
        old_meta["tier"] = "mtm"
        old_meta["migrate_time"] = time.time()
        self.collection.update(old_id, new_metadata=old_meta)

        print(f"[MIGRATE] STM -> MTM: {old_id[:16]}...")

    def retrieve(
        self,
        query_text: str | None = None,
        query_vector: np.ndarray | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        检索记忆。

        策略：先查 STM，不够再查 MTM。

        Args:
            query_text: 文本查询（用于 STM）
            query_vector: 向量查询（用于 MTM）
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        results: list[dict[str, Any]] = []

        # 1. 从 STM 获取最近记忆
        if query_text:
            stm_results = self.collection.retrieve(
                query=query_text,
                index_name="stm_fifo",
                top_k=top_k,
                with_metadata=True,
            )
            for r in stm_results:
                r["source"] = "stm"
            results.extend(stm_results)
            print(f"[RETRIEVE] STM results: {len(stm_results)}")

        # 2. 如果不够，从 MTM 语义检索
        if len(results) < top_k and query_vector is not None:
            mtm_results = self.collection.retrieve(
                query=query_vector,
                index_name="mtm_segment",
                top_k=top_k - len(results),
                with_metadata=True,
            )
            for r in mtm_results:
                r["source"] = "mtm"
            results.extend(mtm_results)
            print(f"[RETRIEVE] MTM results: {len(mtm_results)}")

        return results[:top_k]

    def hybrid_retrieve(
        self,
        query_text: str,
        query_vector: np.ndarray,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        混合检索（RRF 融合）。

        Args:
            query_text: 文本查询
            query_vector: 向量查询
            top_k: 返回数量

        Returns:
            融合后的检索结果
        """
        results = self.collection.retrieve_multi(
            queries={
                "stm_fifo": query_text,
                "mtm_segment": query_vector,
            },
            top_k=top_k,
            fusion_strategy="rrf",
        )
        print(f"[HYBRID] RRF fusion results: {len(results)}")
        return results

    def get_stats(self) -> dict[str, int]:
        """获取统计信息。"""
        return {
            "stm_count": len(self._stm_queue),
            "mtm_count": self.collection.get_index_count("mtm_segment"),
            "ltm_count": self.collection.get_index_count("ltm_archive"),
            "total_data": len(self.collection.text_storage.get_all_ids()),
        }


def demo_basic_flow():
    """演示基本的 MemoryOS 流程。"""
    print("\n" + "=" * 60)
    print("Demo 1: Basic MemoryOS Flow")
    print("=" * 60)

    # 使用小容量便于演示
    service = MemoryOSService(
        stm_capacity=3,
        mtm_capacity=10,
        embedding_dim=4,  # 使用小维度便于演示
    )

    # 模拟插入多条记忆
    memories = [
        "I had breakfast at 8am today",
        "Met with Alice for coffee",
        "Read a book about AI",
        "Went for a walk in the park",
        "Had dinner with family",
    ]

    for i, memory in enumerate(memories):
        # 生成模拟向量
        vector = np.random.randn(4).astype(np.float32)
        vector = vector / np.linalg.norm(vector)

        service.insert(
            content=memory,
            vector=vector,
            metadata={"turn_id": i},
        )
        print()

    # 显示统计
    stats = service.get_stats()
    print(f"\nStats: {stats}")
    print(f"  - STM has {stats['stm_count']} items (capacity=3)")
    print(f"  - MTM has {stats['mtm_count']} items (migrated)")


def demo_retrieval():
    """演示检索功能。"""
    print("\n" + "=" * 60)
    print("Demo 2: Memory Retrieval")
    print("=" * 60)

    service = MemoryOSService(
        stm_capacity=3,
        mtm_capacity=10,
        embedding_dim=4,
    )

    # 插入一些记忆
    memories = [
        ("Python is a great programming language", [1.0, 0.0, 0.0, 0.0]),
        ("Java is used for enterprise applications", [0.0, 1.0, 0.0, 0.0]),
        ("Machine learning requires data", [0.5, 0.5, 0.0, 0.0]),
        ("Deep learning uses neural networks", [0.3, 0.3, 0.4, 0.0]),
        ("AI is transforming the world", [0.2, 0.2, 0.2, 0.4]),
    ]

    for text, vec in memories:
        vector = np.array(vec, dtype=np.float32)
        vector = vector / np.linalg.norm(vector)
        service.insert(content=text, vector=vector)
        print()

    print("\n--- Retrieve: query='programming' ---")
    query_vec = np.array([0.8, 0.2, 0.0, 0.0], dtype=np.float32)
    query_vec = query_vec / np.linalg.norm(query_vec)

    results = service.retrieve(
        query_text="programming",
        query_vector=query_vec,
        top_k=3,
    )
    print("Results:")
    for r in results:
        print(f"  [{r['source']}] {r['text'][:50]}... (score: {r.get('score', 0):.4f})")


def demo_hybrid_retrieval():
    """演示混合检索（RRF 融合）。"""
    print("\n" + "=" * 60)
    print("Demo 3: Hybrid Retrieval (RRF Fusion)")
    print("=" * 60)

    service = MemoryOSService(
        stm_capacity=5,
        mtm_capacity=10,
        embedding_dim=4,
    )

    # 插入记忆到不同层级
    memories = [
        ("Recent: Python 3.12 released", [1.0, 0.0, 0.0, 0.0]),
        ("Recent: AI conference 2024", [0.0, 1.0, 0.0, 0.0]),
        ("Older: Python history", [0.9, 0.1, 0.0, 0.0]),
        ("Older: Machine learning basics", [0.5, 0.5, 0.0, 0.0]),
        ("Older: Deep learning advances", [0.3, 0.3, 0.4, 0.0]),
        ("Older: AI ethics discussion", [0.2, 0.8, 0.0, 0.0]),
    ]

    for text, vec in memories:
        vector = np.array(vec, dtype=np.float32)
        vector = vector / np.linalg.norm(vector)
        service.insert(content=text, vector=vector)

    print()
    print("--- Hybrid Retrieval: text='Python', vector=[0.9, 0.1, 0, 0] ---")
    query_vec = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
    query_vec = query_vec / np.linalg.norm(query_vec)

    results = service.hybrid_retrieve(
        query_text="Python",
        query_vector=query_vec,
        top_k=3,
    )
    print("Fused Results:")
    for r in results:
        print(f"  {r['text'][:50]}... (fused_score: {r.get('fused_score', 0):.4f})")


if __name__ == "__main__":
    print("=" * 60)
    print("MemoryOS Style Example with HybridCollection")
    print("=" * 60)
    print()
    print("核心设计原则:")
    print("  - Service : Collection = 1 : 1")
    print("  - Collection = 一份数据 + 多种类型索引")
    print("  - 索引可以独立增删 (insert_to_index / remove_from_index)")
    print()

    demo_basic_flow()
    demo_retrieval()
    demo_hybrid_retrieval()

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)
