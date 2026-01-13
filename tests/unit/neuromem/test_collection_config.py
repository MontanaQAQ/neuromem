"""Tests for CollectionConfig

验证配置类的功能：
- 从字典创建
- 从 YAML 创建
- 创建 Collection
- 序列化/反序列化
"""

import pytest

from sage.neuromem.config.collection_config import CollectionConfig, IndexConfig


class TestIndexConfig:
    """Tests for IndexConfig"""

    def test_create_from_dict(self):
        """Test creating IndexConfig from dict"""
        data = {"name": "main", "type": "faiss", "config": {"dim": 768}}
        config = IndexConfig.from_dict(data)

        assert config.name == "main"
        assert config.index_type == "faiss"
        assert config.config == {"dim": 768}

    def test_create_from_dict_with_index_type_key(self):
        """Test compatibility with 'index_type' key"""
        data = {"name": "main", "index_type": "bm25", "config": {}}
        config = IndexConfig.from_dict(data)

        assert config.index_type == "bm25"

    def test_to_dict(self):
        """Test serialization to dict"""
        config = IndexConfig(name="main", index_type="graph", config={"directed": True})
        data = config.to_dict()

        assert data == {
            "name": "main",
            "index_type": "graph",
            "config": {"directed": True},
        }


class TestCollectionConfig:
    """Tests for CollectionConfig"""

    def test_create_simple(self):
        """Test creating simple config"""
        config = CollectionConfig(name="test_collection")

        assert config.name == "test_collection"
        assert config.storage_backend == "memory"
        assert config.indexes == []

    def test_create_with_indexes(self):
        """Test creating config with indexes"""
        idx1 = IndexConfig(name="main", index_type="faiss", config={"dim": 768})
        idx2 = IndexConfig(name="graph", index_type="graph", config={})

        config = CollectionConfig(
            name="test",
            storage_backend="redis",
            indexes=[idx1, idx2],
        )

        assert len(config.indexes) == 2
        assert config.indexes[0].name == "main"
        assert config.indexes[1].name == "graph"

    def test_from_dict_legacy_format(self):
        """Test loading from legacy YAML format (with storage.type)"""
        data = {
            "name": "my_collection",
            "storage": {"type": "simple", "config": {"persist_dir": "/tmp"}},
            "indexes": [{"name": "main", "type": "faiss", "config": {"dimension": 768}}],
        }

        config = CollectionConfig.from_dict(data)

        assert config.name == "my_collection"
        # "simple" is automatically converted to "memory"
        assert config.storage_backend == "memory"
        assert config.storage_config == {"persist_dir": "/tmp"}
        assert len(config.indexes) == 1
        # "dimension" is automatically converted to "dim"
        assert config.indexes[0].config["dim"] == 768

    def test_from_dict_new_format(self):
        """Test loading from new format (with storage_backend)"""
        data = {
            "name": "new_collection",
            "storage_backend": "memory",
            "indexes": [{"name": "main", "index_type": "bm25", "config": {}}],
        }

        config = CollectionConfig.from_dict(data)

        assert config.name == "new_collection"
        assert config.storage_backend == "memory"
        assert len(config.indexes) == 1

    def test_to_dict(self):
        """Test serialization"""
        config = CollectionConfig(
            name="test",
            storage_backend="redis",
            storage_config={"host": "localhost"},
            indexes=[IndexConfig("main", "faiss", {"dim": 768})],
            metadata={"version": "2.0"},
        )

        data = config.to_dict()

        assert data["name"] == "test"
        assert data["storage_backend"] == "redis"
        assert data["storage_config"]["host"] == "localhost"
        assert len(data["indexes"]) == 1
        assert data["metadata"]["version"] == "2.0"

    def test_create_collection(self):
        """Test creating UnifiedCollection from config"""
        config = CollectionConfig(
            name="test_create",
            storage_backend="memory",
            indexes=[
                IndexConfig("idx1", "faiss", {"dim": 4}),
            ],
        )

        collection = config.create_collection()

        assert collection.name == "test_create"
        assert "idx1" in collection.indexes
        assert len(collection.indexes) == 1

    def test_create_collection_with_override(self):
        """Test creating collection with parameter override"""
        config = CollectionConfig(
            name="original_name",
            storage_backend="memory",
        )

        collection = config.create_collection(name="overridden_name")

        assert collection.name == "overridden_name"

    def test_repr(self):
        """Test string representation"""
        config = CollectionConfig(
            name="test",
            indexes=[IndexConfig("idx1", "faiss", {})],
        )

        repr_str = repr(config)

        assert "test" in repr_str
        assert "memory" in repr_str
        assert "indexes=1" in repr_str


class TestYAMLIntegration:
    """Tests for YAML loading/saving"""

    def test_from_yaml_legacy(self, tmp_path):
        """Test loading from legacy YAML format"""
        yaml_content = """
collection:
  name: "legacy_collection"
  storage:
    type: "memory"
    config: {}
  indexes:
    - name: "main"
      type: "faiss"
      config:
        dimension: 768
        metric: "cosine"
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        config = CollectionConfig.from_yaml(yaml_file)

        assert config.name == "legacy_collection"
        assert config.storage_backend == "memory"
        assert len(config.indexes) == 1
        # "dimension" is automatically converted to "dim"
        assert config.indexes[0].config["dim"] == 768
        assert config.indexes[0].config["metric"] == "cosine"

    def test_to_yaml(self, tmp_path):
        """Test saving to YAML"""
        config = CollectionConfig(
            name="test",
            storage_backend="memory",
            indexes=[IndexConfig("main", "faiss", {"dim": 768})],
        )

        yaml_file = tmp_path / "output.yaml"
        config.to_yaml(yaml_file)

        assert yaml_file.exists()

        # Reload and verify
        loaded_config = CollectionConfig.from_yaml(yaml_file)
        assert loaded_config.name == "test"
        assert len(loaded_config.indexes) == 1

    def test_from_yaml_not_found(self):
        """Test error when YAML file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            CollectionConfig.from_yaml("nonexistent.yaml")
