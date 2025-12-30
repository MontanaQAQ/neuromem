"""
UnifiedCollection 基础数据管理测试 (T1.1)

测试范围:
- __init__: Collection 初始化
- insert: 数据插入
- get: 数据获取
- delete: 数据删除
- _generate_id: ID 生成稳定性
"""

import sys
from pathlib import Path

# 直接导入 unified_collection 模块，避免导入整个 sage.middleware
neuromem_path = Path(__file__).parent.parent.parent.parent / "memory_collection"
sys.path.insert(0, str(neuromem_path.parent))

import pytest  # noqa: E402

from memory_collection.unified_collection import UnifiedCollection  # noqa: E402


class TestUnifiedCollectionBasic:
    """UnifiedCollection 基础功能测试"""

    def test_init(self):
        """测试 Collection 初始化"""
        coll = UnifiedCollection(name="test_coll")

        assert coll.name == "test_coll"
        assert len(coll.raw_data) == 0
        assert len(coll.indexes) == 0
        assert coll.config == {}

    def test_init_with_config(self):
        """测试带配置的初始化"""
        config = {"persist_path": "/tmp/test"}
        coll = UnifiedCollection(name="test_coll", config=config)

        assert coll.name == "test_coll"
        assert coll.config == config

    def test_insert_basic(self):
        """测试基础插入功能"""
        coll = UnifiedCollection(name="test_coll")

        # 插入数据
        data_id = coll.insert(text="Hello, world!", metadata={"author": "Alice"})

        # 验证返回值
        assert isinstance(data_id, str)
        assert len(data_id) == 64  # SHA256 长度

        # 验证数据存储
        assert data_id in coll.raw_data
        assert coll.raw_data[data_id]["text"] == "Hello, world!"
        assert coll.raw_data[data_id]["metadata"] == {"author": "Alice"}
        assert "created_at" in coll.raw_data[data_id]

        # 验证计数
        assert len(coll) == 1

    def test_insert_without_metadata(self):
        """测试不带 metadata 的插入"""
        coll = UnifiedCollection(name="test_coll")

        data_id = coll.insert(text="No metadata")

        assert data_id in coll.raw_data
        assert coll.raw_data[data_id]["metadata"] == {}

    def test_insert_duplicate_content(self):
        """测试相同内容插入 (应该覆盖)"""
        coll = UnifiedCollection(name="test_coll")

        # 插入第一次
        id1 = coll.insert(text="Same text", metadata={"version": 1})
        assert len(coll) == 1

        # 插入相同内容（metadata 不同）
        id2 = coll.insert(text="Same text", metadata={"version": 2})

        # 由于 text + metadata 都参与 ID 生成，ID 应该不同
        assert id1 != id2
        assert len(coll) == 2

    def test_insert_exact_duplicate(self):
        """测试完全相同的插入 (text + metadata 都相同)"""
        coll = UnifiedCollection(name="test_coll")

        # 插入第一次
        id1 = coll.insert(text="Exact same", metadata={"key": "value"})
        assert len(coll) == 1

        # 插入完全相同的内容
        id2 = coll.insert(text="Exact same", metadata={"key": "value"})

        # ID 应该相同，数据被覆盖
        assert id1 == id2
        assert len(coll) == 1  # 仍然只有 1 条数据

    def test_get_existing(self):
        """测试获取存在的数据"""
        coll = UnifiedCollection(name="test_coll")

        data_id = coll.insert(text="Test data", metadata={"key": "value"})
        result = coll.get(data_id)

        assert result is not None
        assert result["text"] == "Test data"
        assert result["metadata"] == {"key": "value"}
        assert "created_at" in result

    def test_get_nonexistent(self):
        """测试获取不存在的数据"""
        coll = UnifiedCollection(name="test_coll")

        result = coll.get("nonexistent_id")
        assert result is None

    def test_delete_existing(self):
        """测试删除存在的数据"""
        coll = UnifiedCollection(name="test_coll")

        data_id = coll.insert(text="To be deleted")
        assert len(coll) == 1

        # 删除数据
        success = coll.delete(data_id)

        assert success is True
        assert data_id not in coll.raw_data
        assert len(coll) == 0

    def test_delete_nonexistent(self):
        """测试删除不存在的数据"""
        coll = UnifiedCollection(name="test_coll")

        success = coll.delete("nonexistent_id")
        assert success is False

    def test_generate_id_stability(self):
        """测试 ID 生成的稳定性"""
        coll = UnifiedCollection(name="test_coll")

        # 相同内容应该生成相同 ID
        id1 = coll._generate_id("test", {"key": "value"})
        id2 = coll._generate_id("test", {"key": "value"})
        assert id1 == id2

        # metadata 顺序不影响结果
        id3 = coll._generate_id("test", {"key": "value", "other": 1})
        id4 = coll._generate_id("test", {"other": 1, "key": "value"})
        assert id3 == id4

        # 不同内容应该生成不同 ID
        id5 = coll._generate_id("different", {"key": "value"})
        assert id1 != id5

    def test_contains(self):
        """测试 __contains__ 方法"""
        coll = UnifiedCollection(name="test_coll")

        data_id = coll.insert(text="Test")
        assert data_id in coll
        assert "nonexistent_id" not in coll

    def test_len(self):
        """测试 __len__ 方法"""
        coll = UnifiedCollection(name="test_coll")

        assert len(coll) == 0

        coll.insert(text="Data 1")
        assert len(coll) == 1

        coll.insert(text="Data 2")
        assert len(coll) == 2

    def test_repr(self):
        """测试 __repr__ 方法"""
        coll = UnifiedCollection(name="test_coll")
        coll.insert(text="Data")

        repr_str = repr(coll)
        assert "UnifiedCollection" in repr_str
        assert "test_coll" in repr_str
        assert "data_count=1" in repr_str
        assert "index_count=0" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
