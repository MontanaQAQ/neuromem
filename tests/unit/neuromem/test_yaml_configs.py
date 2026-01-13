"""Test loading all existing YAML configurations

验证所有现有的 YAML 配置文件能被 CollectionConfig 正确加载。
"""

from pathlib import Path

import pytest

from sage.neuromem.config.collection_config import CollectionConfig


class TestExistingYAMLConfigs:
    """Test loading all existing YAML configuration files"""

    @pytest.fixture
    def config_dir(self):
        """Get the config directory path"""
        return Path(__file__).parent.parent.parent.parent / "sage" / "neuromem" / "config"

    def test_all_yaml_files_loadable(self, config_dir):
        """Test that all YAML files in config/ can be loaded"""
        yaml_files = list(config_dir.glob("*.yaml"))
        assert len(yaml_files) > 0, "No YAML files found in config directory"

        loaded_configs = {}
        errors = {}

        for yaml_file in yaml_files:
            try:
                config = CollectionConfig.from_yaml(yaml_file)
                loaded_configs[yaml_file.name] = config
                print(f"✓ {yaml_file.name}: {config.name} ({len(config.indexes)} indexes)")
            except Exception as e:
                errors[yaml_file.name] = str(e)
                print(f"✗ {yaml_file.name}: {e}")

        # Report results
        print(f"\nLoaded {len(loaded_configs)}/{len(yaml_files)} configs successfully")

        if errors:
            print("\nErrors:")
            for filename, error in errors.items():
                print(f"  {filename}: {error}")
            pytest.fail(f"Failed to load {len(errors)} YAML files")

    @pytest.mark.parametrize(
        "yaml_file",
        [
            "feature_graph_vectorstore.yaml",
            "feature_knowledge_graph.yaml",
            "feature_queue_segment.yaml",
            "feature_queue_vectorstore.yaml",
            "feature_summary_vectorstore.yaml",
            "graph_inverted.yaml",
            "inverted_vectorstore.yaml",
            "keyword_graph.yaml",
            "lsh_inverted.yaml",
            "semantic_graph.yaml",
            "semantic_inverted.yaml",
            "semantic_inverted_kg.yaml",
            "topic_segment_summary.yaml",
        ],
    )
    def test_individual_yaml_files(self, config_dir, yaml_file):
        """Test loading each YAML file individually"""
        yaml_path = config_dir / yaml_file
        assert yaml_path.exists(), f"YAML file not found: {yaml_file}"

        config = CollectionConfig.from_yaml(yaml_path)

        # Basic validations
        assert config.name, f"{yaml_file}: Missing collection name"
        assert config.storage_backend, f"{yaml_file}: Missing storage backend"

        # Indexes should be loaded (most configs have at least one index)
        print(f"{yaml_file}: {config.name} - {len(config.indexes)} indexes")

    def test_create_collections_from_yaml(self, config_dir):
        """Test creating UnifiedCollection instances from YAML configs"""
        yaml_files = [
            "feature_knowledge_graph.yaml",
            "semantic_inverted.yaml",
        ]

        for yaml_file in yaml_files:
            yaml_path = config_dir / yaml_file
            config = CollectionConfig.from_yaml(yaml_path)

            # Create collection (should not raise)
            collection = config.create_collection()

            assert collection.name == config.name
            assert len(collection.indexes) == len(config.indexes)

            print(f"✓ Created collection from {yaml_file}: {collection}")
