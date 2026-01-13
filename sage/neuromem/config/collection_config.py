"""CollectionConfig - 统一的 Collection 配置类

提供结构化的配置管理，支持从字典/YAML 创建 UnifiedCollection。

典型用法：
    >>> # 从字典创建
    >>> config = CollectionConfig(
    ...     name="my_collection",
    ...     storage_backend="memory",
    ...     indexes=[
    ...         IndexConfig(name="main", index_type="faiss", dim=768),
    ...     ],
    ... )
    >>>
    >>> # 从 YAML 创建
    >>> config = CollectionConfig.from_yaml("config/my_config.yaml")
    >>>
    >>> # 创建 Collection
    >>> collection = config.create_collection()
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class IndexConfig:
    """索引配置

    Attributes:
        name: 索引名称（如 "main", "semantic", "graph"）
        index_type: 索引类型（faiss, bm25, graph, fifo, segment, lsh）
        config: 索引特定配置（dim, metric, max_size 等）
    """

    name: str
    index_type: str
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IndexConfig:
        """从字典创建

        Args:
            data: 包含 name, type, config 的字典

        Returns:
            IndexConfig 实例

        Example:
            >>> data = {
            ...     "name": "main",
            ...     "type": "faiss",
            ...     "config": {"dim": 768, "metric": "cosine"}
            ... }
            >>> idx_config = IndexConfig.from_dict(data)
        """
        # 兼容 type 和 index_type 两种键名
        index_type = data.get("index_type") or data.get("type")
        if not index_type:
            raise ValueError("IndexConfig requires 'type' or 'index_type' field")

        # 获取配置并进行兼容性转换
        config = data.get("config", {}).copy()

        # 兼容 dimension -> dim（FAISS 索引）
        if "dimension" in config and "dim" not in config:
            config["dim"] = config.pop("dimension")

        return cls(
            name=data["name"],
            index_type=index_type,
            config=config,
        )


@dataclass
class CollectionConfig:
    """UnifiedCollection 配置类

    提供统一的配置管理，支持从 YAML/字典创建。

    Attributes:
        name: Collection 名称
        storage_backend: 存储后端类型（memory, redis, sagedb）
        storage_config: 存储后端配置
        indexes: 索引配置列表
        metadata: 额外的元数据（如 description, version）
    """

    name: str
    storage_backend: str = "memory"
    storage_config: dict[str, Any] = field(default_factory=dict)
    indexes: list[IndexConfig] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            包含所有配置的字典，格式兼容 YAML

        Example:
            >>> config = CollectionConfig(name="test", indexes=[...])
            >>> data = config.to_dict()
            >>> print(data)
            {
                "name": "test",
                "storage_backend": "memory",
                ...
            }
        """
        return {
            "name": self.name,
            "storage_backend": self.storage_backend,
            "storage_config": self.storage_config,
            "indexes": [idx.to_dict() for idx in self.indexes],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CollectionConfig:
        """从字典创建配置

        Args:
            data: 包含 collection 配置的字典

        Returns:
            CollectionConfig 实例

        Example:
            >>> data = {
            ...     "name": "my_collection",
            ...     "storage": {"type": "memory"},
            ...     "indexes": [
            ...         {"name": "main", "type": "faiss", "config": {"dim": 768}}
            ...     ]
            ... }
            >>> config = CollectionConfig.from_dict(data)
        """
        # 兼容 storage.type 和 storage_backend 两种格式
        storage_data = data.get("storage", {})
        storage_backend = data.get("storage_backend") or storage_data.get("type", "memory")
        storage_config = data.get("storage_config") or storage_data.get("config", {})

        # 兼容旧的 "simple" 存储类型（映射到 "memory"）
        if storage_backend == "simple":
            storage_backend = "memory"

        # 解析索引配置
        indexes_data = data.get("indexes", [])
        indexes = [IndexConfig.from_dict(idx_data) for idx_data in indexes_data]

        return cls(
            name=data["name"],
            storage_backend=storage_backend,
            storage_config=storage_config,
            indexes=indexes,
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> CollectionConfig:
        """从 YAML 文件创建配置

        Args:
            yaml_path: YAML 配置文件路径

        Returns:
            CollectionConfig 实例

        Raises:
            FileNotFoundError: YAML 文件不存在
            yaml.YAMLError: YAML 格式错误

        Example:
            >>> config = CollectionConfig.from_yaml("config/my_config.yaml")
            >>> collection = config.create_collection()
        """
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML config not found: {yaml_path}")

        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 支持多种 YAML 格式：
        # 1. collection 嵌套格式：{"collection": {...}}
        # 2. 顶层 indexes：{"collection": {...}, "indexes": [...]}
        # 3. 扁平格式：直接在顶层定义所有字段

        if "collection" in data:
            collection_data = data["collection"].copy()
            # 如果 indexes 在顶层，合并到 collection_data
            if "indexes" in data and "indexes" not in collection_data:
                collection_data["indexes"] = data["indexes"]
        else:
            collection_data = data

        return cls.from_dict(collection_data)

    def to_yaml(self, yaml_path: str | Path) -> None:
        """保存配置到 YAML 文件

        Args:
            yaml_path: 目标 YAML 文件路径

        Example:
            >>> config.to_yaml("config/output.yaml")
        """
        yaml_path = Path(yaml_path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        data = {"collection": self.to_dict()}

        with yaml_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def create_collection(self, **kwargs: Any):
        """根据配置创建 UnifiedCollection

        Args:
            **kwargs: 额外的 UnifiedCollection 参数（会覆盖配置中的值）

        Returns:
            UnifiedCollection 实例（已添加所有配置的索引）

        Example:
            >>> config = CollectionConfig.from_yaml("config/my_config.yaml")
            >>> collection = config.create_collection()
            >>> # Collection 已经包含配置中定义的所有索引
        """
        from ..memory_collection.unified_collection import UnifiedCollection

        # 合并参数：kwargs 优先级更高
        init_params = {
            "name": self.name,
            "storage_backend": self.storage_backend,
            "storage_config": self.storage_config,
            **kwargs,
        }

        # 创建 Collection
        collection = UnifiedCollection(**init_params)

        # 添加索引
        for idx_config in self.indexes:
            collection.add_index(
                name=idx_config.name,
                index_type=idx_config.index_type,
                config=idx_config.config,
            )

        return collection

    def __repr__(self) -> str:
        """返回配置的字符串表示"""
        return (
            f"CollectionConfig(name='{self.name}', "
            f"storage='{self.storage_backend}', "
            f"indexes={len(self.indexes)})"
        )
