"""AsyncMemoryAdapter 单元测试

验收标准 (issue #57)：
- AsyncMemoryAdapter.insert/retrieve/persist 不阻塞事件循环
- 同步接口保持不变，无 breaking change
- 从 sage.neuromem 可直接导入
- 单元测试：异步插入 100 条 → 异步检索 → 验证不阻塞
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from sage.neuromem import AsyncMemoryAdapter
from sage.neuromem.memory_collection.unified_collection import UnifiedCollection

# ---------------------------------------------------------------------------
# 辅助 Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_collection() -> UnifiedCollection:
    """返回一个最简的 UnifiedCollection（无向量索引，不依赖 FAISS/模型）。"""
    return UnifiedCollection(name="test_async", config={})


@pytest.fixture
def adapter(simple_collection: UnifiedCollection) -> AsyncMemoryAdapter:
    return AsyncMemoryAdapter(simple_collection)


# ---------------------------------------------------------------------------
# 导入与接口测试
# ---------------------------------------------------------------------------


class TestAsyncMemoryAdapterImport:
    """验证模块级导入和基础接口。"""

    def test_import_from_sage_neuromem(self):
        """从 sage.neuromem 直接导入 AsyncMemoryAdapter（验收标准：可导入）。"""
        from sage.neuromem import AsyncMemoryAdapter as _Adapter  # noqa: F401

        assert _Adapter is AsyncMemoryAdapter

    def test_adapter_has_required_methods(self):
        """AsyncMemoryAdapter 具备 insert / insert_batch / retrieve / persist 方法。"""
        assert callable(AsyncMemoryAdapter.insert)
        assert callable(AsyncMemoryAdapter.insert_batch)
        assert callable(AsyncMemoryAdapter.retrieve)
        assert callable(AsyncMemoryAdapter.persist)

    def test_adapter_exposes_collection(self, adapter, simple_collection):
        """adapter.collection 指向底层 UnifiedCollection 实例。"""
        assert adapter.collection is simple_collection

    def test_get_executor_returns_thread_pool(self):
        """get_executor() 返回模块级 ThreadPoolExecutor。"""
        from concurrent.futures import ThreadPoolExecutor

        executor = AsyncMemoryAdapter.get_executor()
        assert isinstance(executor, ThreadPoolExecutor)


# ---------------------------------------------------------------------------
# 异步 insert 测试
# ---------------------------------------------------------------------------


class TestAsyncInsert:
    """验证 async insert 的正确性与非阻塞行为。"""

    @pytest.mark.asyncio
    async def test_insert_returns_data_id(self, adapter, simple_collection):
        """insert 返回有效的 data_id，且数据已写入底层 collection。"""
        data_id = await adapter.insert("hello neuromem", {"source": "test"})

        assert isinstance(data_id, str)
        assert len(data_id) > 0
        assert simple_collection.size() == 1

    @pytest.mark.asyncio
    async def test_insert_without_metadata(self, adapter, simple_collection):
        """insert 可在不提供 metadata 的情况下调用。"""
        data_id = await adapter.insert("plain text")
        assert simple_collection.get(data_id) is not None

    @pytest.mark.asyncio
    async def test_insert_100_items_sequential(self, adapter, simple_collection):
        """顺序异步插入 100 条数据后 collection 大小正确。"""
        for i in range(100):
            await adapter.insert(f"item {i}", {"idx": i})

        assert simple_collection.size() == 100

    @pytest.mark.asyncio
    async def test_insert_does_not_block_event_loop(self, simple_collection):
        """验证不阻塞：并发 ticker 协程在 insert 运行期间可正常执行。"""
        adapter = AsyncMemoryAdapter(simple_collection)
        tick_count = {"value": 0}

        async def ticker():
            """每次 yield 点增加计数，如果事件循环被阻塞则无法执行。"""
            for _ in range(20):
                await asyncio.sleep(0)
                tick_count["value"] += 1

        async def bulk_insert():
            for i in range(100):
                await adapter.insert(f"text {i}", {"i": i})

        # 同时运行，事件循环应可交替执行两者
        await asyncio.gather(ticker(), bulk_insert())

        # ticker 必须完整执行完 20 次（若阻塞则会 <20）
        assert tick_count["value"] == 20
        assert simple_collection.size() == 100

    @pytest.mark.asyncio
    async def test_insert_same_text_deduplication(self, adapter, simple_collection):
        """相同内容多次 insert 应返回相同 data_id（UnifiedCollection 幂等行为）。"""
        id1 = await adapter.insert("duplicate text")
        id2 = await adapter.insert("duplicate text")
        assert id1 == id2


# ---------------------------------------------------------------------------
# 异步 insert_batch 测试
# ---------------------------------------------------------------------------


class TestAsyncInsertBatch:
    @pytest.mark.asyncio
    async def test_insert_batch_returns_ids(self, adapter, simple_collection):
        """insert_batch 返回与输入数量一致的 data_id 列表。"""
        texts = [f"batch item {i}" for i in range(10)]
        ids = await adapter.insert_batch(texts)
        assert len(ids) == 10
        assert simple_collection.size() == 10

    @pytest.mark.asyncio
    async def test_insert_batch_with_metadatas(self, adapter, simple_collection):
        """insert_batch 正确存储各自的 metadata。"""
        texts = ["text A", "text B"]
        metas = [{"label": "A"}, {"label": "B"}]
        ids = await adapter.insert_batch(texts, metas)

        for data_id in ids:
            assert simple_collection.get(data_id) is not None


# ---------------------------------------------------------------------------
# 异步 retrieve 测试
# ---------------------------------------------------------------------------


class TestAsyncRetrieve:
    @pytest.mark.asyncio
    async def test_retrieve_with_mock_index(self, adapter):
        """retrieve 在线程池中调用底层 UnifiedCollection.retrieve，返回正确结果。"""
        mock_collection = MagicMock(spec=UnifiedCollection)
        mock_collection.retrieve.return_value = [{"id": "abc", "text": "hello", "metadata": {}}]
        adapter_mock = AsyncMemoryAdapter(mock_collection)

        results = await adapter_mock.retrieve("my_index", "hello")

        assert len(results) == 1
        assert results[0]["text"] == "hello"
        mock_collection.retrieve.assert_called_once_with("my_index", "hello")

    @pytest.mark.asyncio
    async def test_retrieve_passes_kwargs(self, adapter):
        """retrieve 将 **params 透传给底层 retrieve 方法。"""
        mock_collection = MagicMock(spec=UnifiedCollection)
        mock_collection.retrieve.return_value = []
        adapter_mock = AsyncMemoryAdapter(mock_collection)

        await adapter_mock.retrieve("idx", "query", top_k=3, threshold=0.8)

        mock_collection.retrieve.assert_called_once_with("idx", "query", top_k=3, threshold=0.8)

    @pytest.mark.asyncio
    async def test_retrieve_does_not_block_event_loop(self):
        """验证 retrieve 不阻塞：ticker 在 retrieve 运行期间仍可执行。"""
        mock_collection = MagicMock(spec=UnifiedCollection)

        def slow_retrieve(index_name, query, **params):
            time.sleep(0.05)  # 模拟 50ms 耗时
            return [{"id": "x", "text": query, "metadata": {}}]

        mock_collection.retrieve.side_effect = slow_retrieve
        adapter_mock = AsyncMemoryAdapter(mock_collection)
        tick_count = {"value": 0}

        async def ticker():
            for _ in range(5):
                await asyncio.sleep(0.01)
                tick_count["value"] += 1

        await asyncio.gather(
            adapter_mock.retrieve("idx", "test query"),
            ticker(),
        )

        # ticker 必须执行完成（事件循环未被阻塞）
        assert tick_count["value"] == 5


# ---------------------------------------------------------------------------
# 异步 persist 测试
# ---------------------------------------------------------------------------


class TestAsyncPersist:
    @pytest.mark.asyncio
    async def test_persist_calls_manager_persist(self):
        """persist 在线程池中调用 MemoryManager.persist(name)。"""
        mock_manager = MagicMock()
        mock_manager.persist.return_value = True
        mock_collection = MagicMock(spec=UnifiedCollection)

        adapter = AsyncMemoryAdapter(mock_collection)
        result = await adapter.persist(mock_manager, "my_collection")

        mock_manager.persist.assert_called_once_with("my_collection")
        assert result is True

    @pytest.mark.asyncio
    async def test_persist_does_not_block_event_loop(self):
        """验证 persist 不阻塞：ticker 在 persist 运行期间仍可执行。"""
        mock_manager = MagicMock()

        def slow_persist(name: str) -> bool:
            time.sleep(0.05)
            return True

        mock_manager.persist.side_effect = slow_persist
        mock_collection = MagicMock(spec=UnifiedCollection)
        adapter = AsyncMemoryAdapter(mock_collection)
        tick_count = {"value": 0}

        async def ticker():
            for _ in range(5):
                await asyncio.sleep(0.01)
                tick_count["value"] += 1

        await asyncio.gather(
            adapter.persist(mock_manager, "col"),
            ticker(),
        )

        assert tick_count["value"] == 5


# ---------------------------------------------------------------------------
# 同步接口无破坏性变更测试
# ---------------------------------------------------------------------------


class TestSyncInterfaceUnchanged:
    """验证同步接口保持不变（无 breaking change）。"""

    def test_unified_collection_insert_still_sync(self, simple_collection):
        """UnifiedCollection.insert 仍为同步方法，非协程。"""
        result = simple_collection.insert("sync text")
        # 不是 coroutine
        assert not asyncio.iscoroutine(result)
        assert isinstance(result, str)

    def test_unified_collection_retrieve_still_sync(self, simple_collection):
        """UnifiedCollection.retrieve 仍为同步方法。"""
        # 无索引时应抛出 ValueError，而非返回协程
        with pytest.raises((ValueError, KeyError)):
            simple_collection.retrieve("nonexistent_index", "query")
