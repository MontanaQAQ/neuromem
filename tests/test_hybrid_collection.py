"""
Unit tests for HybridCollection - Part 6 of NeuroMem Refactor.

测试核心设计原则：
- Collection = 一份数据 + 多种类型索引
- 数据只存一份，索引可以有多个
- 索引可以独立增删（insert_to_index / remove_from_index）
"""

import numpy as np
import pytest
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    HybridCollection,
    IndexType,
)


class TestHybridCollectionBasic:
    """HybridCollection 基础功能测试。"""

    def test_init(self):
        """测试初始化。"""
        collection = HybridCollection({"name": "test_hybrid"})
        assert collection.name == "test_hybrid"
        assert len(collection.list_indexes()) == 0

    def test_create_vdb_index(self):
        """测试创建 VDB 索引。"""
        collection = HybridCollection({"name": "test_vdb"})
        result = collection.create_index(
            {
                "name": "semantic",
                "type": "vdb",
                "dim": 768,
                "backend_type": "FAISS",
            }
        )
        assert result is True
        assert "semantic" in collection.vdb_indexes
        assert collection.get_index_type("semantic") == IndexType.VDB

    def test_create_kv_index(self):
        """测试创建 KV 索引。"""
        collection = HybridCollection({"name": "test_kv"})
        result = collection.create_index(
            {
                "name": "keyword",
                "type": "kv",
                "index_type": "bm25s",
            }
        )
        assert result is True
        assert "keyword" in collection.kv_indexes
        assert collection.get_index_type("keyword") == IndexType.KV

    def test_create_graph_index(self):
        """测试创建 Graph 索引。"""
        collection = HybridCollection({"name": "test_graph"})
        result = collection.create_index(
            {
                "name": "relation",
                "type": "graph",
                "index_type": "simple",
            }
        )
        assert result is True
        assert "relation" in collection.graph_indexes
        assert collection.get_index_type("relation") == IndexType.GRAPH

    def test_create_multiple_indexes(self):
        """测试创建多种类型索引。"""
        collection = HybridCollection({"name": "test_multi"})

        # VDB 索引
        collection.create_index(
            {
                "name": "vdb_1",
                "type": "vdb",
                "dim": 384,
                "backend_type": "FAISS",
            }
        )

        # KV 索引
        collection.create_index(
            {
                "name": "kv_1",
                "type": "kv",
                "index_type": "bm25s",
            }
        )

        # Graph 索引
        collection.create_index(
            {
                "name": "graph_1",
                "type": "graph",
                "index_type": "simple",
            }
        )

        indexes = collection.list_indexes()
        assert len(indexes) == 3
        assert {idx["name"] for idx in indexes} == {"vdb_1", "kv_1", "graph_1"}

    def test_delete_index(self):
        """测试删除索引。"""
        collection = HybridCollection({"name": "test_delete"})
        collection.create_index(
            {
                "name": "to_delete",
                "type": "kv",
            }
        )

        assert collection.delete_index("to_delete") is True
        assert "to_delete" not in collection.kv_indexes
        assert collection.delete_index("nonexistent") is False


class TestHybridCollectionDataOperations:
    """HybridCollection 数据操作测试。"""

    @pytest.fixture
    def hybrid_collection(self):
        """创建带有多种索引的 HybridCollection。"""
        collection = HybridCollection({"name": "test_data_ops"})

        # 创建 VDB 索引
        collection.create_index(
            {
                "name": "semantic",
                "type": "vdb",
                "dim": 4,
                "backend_type": "FAISS",
            }
        )

        # 创建 KV 索引
        collection.create_index(
            {
                "name": "keyword",
                "type": "kv",
                "index_type": "bm25s",
            }
        )

        # 创建 Graph 索引
        collection.create_index(
            {
                "name": "relation",
                "type": "graph",
            }
        )

        return collection

    def test_insert_data_only(self, hybrid_collection):
        """测试只插入数据不建索引。"""
        item_id = hybrid_collection.insert(
            content="Hello, World!",
            metadata={"source": "test"},
        )

        assert item_id is not None
        assert hybrid_collection.text_storage.has(item_id)
        assert hybrid_collection.get_text(item_id) == "Hello, World!"

    def test_insert_to_vdb_index(self, hybrid_collection):
        """测试插入到 VDB 索引。"""
        vector = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        item_id = hybrid_collection.insert(
            content="VDB content",
            index_names=["semantic"],
            vector=vector,
        )

        # 验证数据存储
        assert hybrid_collection.text_storage.has(item_id)

        # 验证可以检索
        query_vec = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        results = hybrid_collection.retrieve(
            query=query_vec,
            index_name="semantic",
            top_k=1,
        )
        assert len(results) == 1
        assert results[0]["text"] == "VDB content"

    def test_insert_to_kv_index(self, hybrid_collection):
        """测试插入到 KV 索引。"""
        item_id = hybrid_collection.insert(
            content="Python programming is great",
            index_names=["keyword"],
        )

        # 验证数据存储
        assert hybrid_collection.text_storage.has(item_id)

        # 验证可以检索
        results = hybrid_collection.retrieve(
            query="Python",
            index_name="keyword",
            top_k=1,
        )
        assert len(results) == 1
        assert "Python" in results[0]["text"]

    def test_insert_to_graph_index(self, hybrid_collection):
        """测试插入到 Graph 索引。"""
        # 插入两个节点
        id1 = hybrid_collection.insert(
            content="Node A content",
            index_names=["relation"],
        )
        id2 = hybrid_collection.insert(
            content="Node B content",
            index_names=["relation"],
            edges=[(id1, 1.0)],  # B -> A
        )

        # 验证节点存在
        assert hybrid_collection.text_storage.has(id1)
        assert hybrid_collection.text_storage.has(id2)

        # 验证图结构
        graph = hybrid_collection.graph_indexes["relation"]
        assert graph.has_node(id1)
        assert graph.has_node(id2)

    def test_insert_to_multiple_indexes(self, hybrid_collection):
        """测试同时插入到多个索引。"""
        vector = np.array([0.5, 0.5, 0.0, 0.0], dtype=np.float32)
        hybrid_collection.insert(
            content="Multi-index content",
            index_names=["semantic", "keyword"],
            vector=vector,
        )

        # VDB 检索
        vdb_results = hybrid_collection.retrieve(
            query=vector,
            index_name="semantic",
            top_k=1,
        )
        assert len(vdb_results) == 1

        # KV 检索
        kv_results = hybrid_collection.retrieve(
            query="Multi",
            index_name="keyword",
            top_k=1,
        )
        assert len(kv_results) == 1

        # 确认是同一条数据
        assert vdb_results[0]["id"] == kv_results[0]["id"]


class TestHybridCollectionIndexMigration:
    """HybridCollection 索引迁移测试 - MemoryOS 核心场景。"""

    @pytest.fixture
    def memoryos_collection(self):
        """模拟 MemoryOS 场景：FIFO + Segment 索引。"""
        collection = HybridCollection({"name": "memory_os_test"})

        # FIFO 索引（短期记忆）
        collection.create_index(
            {
                "name": "fifo",
                "type": "kv",
                "index_type": "bm25s",
            }
        )

        # Segment 索引（长期语义记忆）
        collection.create_index(
            {
                "name": "segment",
                "type": "vdb",
                "dim": 4,
                "backend_type": "FAISS",
            }
        )

        return collection

    def test_insert_to_index_existing_data(self, memoryos_collection):
        """测试将已有数据加入新索引。"""
        # 1. 先只存数据，不建索引
        item_id = memoryos_collection.insert(
            content="Memory content",
            metadata={"tier": "stm"},
        )

        # 2. 后续加入 FIFO 索引
        result = memoryos_collection.insert_to_index(
            item_id=item_id,
            index_name="fifo",
        )
        assert result is True

        # 3. 验证可以检索
        results = memoryos_collection.retrieve(
            query="Memory",
            index_name="fifo",
            top_k=1,
        )
        assert len(results) == 1

    def test_remove_from_index_keep_data(self, memoryos_collection):
        """测试从索引移除但保留数据 - MemoryOS 核心操作。"""
        # 1. 插入到 FIFO 索引
        item_id = memoryos_collection.insert(
            content="To be migrated",
            index_names=["fifo"],
        )

        # 验证在 FIFO 中
        fifo_results = memoryos_collection.retrieve(
            query="migrated",
            index_name="fifo",
            top_k=1,
        )
        assert len(fifo_results) == 1

        # 2. 从 FIFO 移除
        result = memoryos_collection.remove_from_index(item_id, "fifo")
        assert result is True

        # 3. 验证 FIFO 中已经没有了
        fifo_results_after = memoryos_collection.retrieve(
            query="migrated",
            index_name="fifo",
            top_k=1,
        )
        assert len(fifo_results_after) == 0

        # 4. 但数据仍然存在
        assert memoryos_collection.text_storage.has(item_id)
        assert memoryos_collection.get_text(item_id) == "To be migrated"

    def test_memoryos_migration_flow(self, memoryos_collection):
        """测试完整的 MemoryOS 迁移流程：FIFO -> Segment。"""
        vector = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

        # 1. 新记忆插入 FIFO
        item_id = memoryos_collection.insert(
            content="New memory",
            index_names=["fifo"],
            metadata={"tier": "stm", "timestamp": 1234567890},
        )

        # 验证在 FIFO 中
        assert (
            len(
                memoryos_collection.retrieve(
                    query="memory",
                    index_name="fifo",
                    top_k=1,
                )
            )
            == 1
        )

        # 2. 从 FIFO 移除（模拟 FIFO 满了，要迁移）
        memoryos_collection.remove_from_index(item_id, "fifo")

        # 3. 加入 Segment 索引（长期语义记忆）
        memoryos_collection.insert_to_index(
            item_id=item_id,
            index_name="segment",
            vector=vector,
        )

        # 4. 验证：FIFO 中没有，Segment 中有
        assert (
            len(
                memoryos_collection.retrieve(
                    query="memory",
                    index_name="fifo",
                    top_k=1,
                )
            )
            == 0
        )

        segment_results = memoryos_collection.retrieve(
            query=vector,
            index_name="segment",
            top_k=1,
        )
        assert len(segment_results) == 1
        assert segment_results[0]["text"] == "New memory"

        # 5. 数据仍然只有一份
        assert memoryos_collection.text_storage.has(item_id)

    def test_delete_removes_from_all_indexes(self, memoryos_collection):
        """测试完全删除时从所有索引移除。"""
        vector = np.array([0.5, 0.5, 0.0, 0.0], dtype=np.float32)

        # 插入到两个索引
        item_id = memoryos_collection.insert(
            content="To be deleted",
            index_names=["fifo"],
        )
        memoryos_collection.insert_to_index(item_id, "segment", vector=vector)

        # 完全删除
        result = memoryos_collection.delete(item_id)
        assert result is True

        # 验证：数据和所有索引都清空
        assert not memoryos_collection.text_storage.has(item_id)

        assert (
            len(
                memoryos_collection.retrieve(
                    query="deleted",
                    index_name="fifo",
                    top_k=1,
                )
            )
            == 0
        )

        assert (
            len(
                memoryos_collection.retrieve(
                    query=vector,
                    index_name="segment",
                    top_k=1,
                )
            )
            == 0
        )


class TestHybridCollectionMultiIndexRetrieval:
    """HybridCollection 多索引检索测试。"""

    @pytest.fixture
    def hybrid_with_data(self):
        """创建带有数据的 HybridCollection。"""
        collection = HybridCollection({"name": "test_multi_retrieval"})

        # VDB 索引
        collection.create_index(
            {
                "name": "semantic",
                "type": "vdb",
                "dim": 4,
                "backend_type": "FAISS",
            }
        )

        # KV 索引
        collection.create_index(
            {
                "name": "keyword",
                "type": "kv",
            }
        )

        # 插入测试数据
        vectors = [
            np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
            np.array([0.5, 0.5, 0.0, 0.0], dtype=np.float32),
        ]
        texts = [
            "Python programming language",
            "Java programming language",
            "Both Python and Java",
        ]

        for i, (text, vec) in enumerate(zip(texts, vectors)):
            collection.insert(
                content=text,
                index_names=["semantic", "keyword"],
                vector=vec,
                metadata={"doc_id": i},
            )

        return collection

    def test_rrf_fusion(self, hybrid_with_data):
        """测试 RRF 融合检索。"""
        query_vec = np.array([0.7, 0.3, 0.0, 0.0], dtype=np.float32)

        results = hybrid_with_data.retrieve_multi(
            queries={
                "semantic": query_vec,
                "keyword": "Python",
            },
            top_k=3,
            fusion_strategy="rrf",
        )

        assert len(results) > 0
        # 结果应该包含 fused_score
        assert "fused_score" in results[0]

    def test_weighted_fusion(self, hybrid_with_data):
        """测试加权融合检索。"""
        query_vec = np.array([0.7, 0.3, 0.0, 0.0], dtype=np.float32)

        results = hybrid_with_data.retrieve_multi(
            queries={
                "semantic": query_vec,
                "keyword": "Python",
            },
            top_k=3,
            fusion_strategy="weighted",
            weights={"semantic": 0.7, "keyword": 0.3},
        )

        assert len(results) > 0
        assert "fused_score" in results[0]

    def test_union_fusion(self, hybrid_with_data):
        """测试 Union 融合（去重合并）。"""
        query_vec = np.array([0.7, 0.3, 0.0, 0.0], dtype=np.float32)

        results = hybrid_with_data.retrieve_multi(
            queries={
                "semantic": query_vec,
                "keyword": "Java",
            },
            top_k=5,
            fusion_strategy="union",
        )

        # 验证无重复
        ids = [r["id"] for r in results]
        assert len(ids) == len(set(ids))


class TestHybridCollectionMetadata:
    """HybridCollection 元数据功能测试。"""

    def test_metadata_filter(self):
        """测试元数据过滤。"""
        collection = HybridCollection({"name": "test_metadata"})
        collection.create_index(
            {
                "name": "kv",
                "type": "kv",
            }
        )

        # 插入带元数据的数据
        collection.insert("Doc A", index_names=["kv"], metadata={"category": "tech"})
        collection.insert("Doc B", index_names=["kv"], metadata={"category": "health"})
        collection.insert("Doc C", index_names=["kv"], metadata={"category": "tech"})

        # 使用元数据过滤
        results = collection.retrieve(
            query="Doc",
            index_name="kv",
            top_k=10,
            with_metadata=True,
            metadata_filter=lambda m: m.get("category") == "tech",
        )

        # 只返回 tech 类别
        assert all(r["metadata"].get("category") == "tech" for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
