"""MemoryManager - UnifiedCollection 生命周期管理器

职责：
- 创建/获取/删除 UnifiedCollection
- 持久化/加载 Collection
- 懒加载支持（按需从磁盘加载）
- 统一路径管理

典型用法：
    >>> manager = MemoryManager()
    >>> # 创建新集合
    >>> collection = manager.create_collection("my_data")
    >>> collection.insert("id1", {"text": "hello"})
    >>> # 持久化
    >>> manager.persist("my_data")
    >>> # 稍后加载
    >>> loaded = manager.get_collection("my_data")  # 自动从磁盘加载
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from sage.common.utils.logging.custom_logger import CustomLogger

from .memory_collection import UnifiedCollection
from .memory_collection.indexes import IndexFactory
from .utils.path_utils import get_default_data_dir


class MemoryManager:
    """UnifiedCollection 生命周期管理器

    管理 Collection 的创建、持久化、加载、删除等操作。

    属性：
        collections: 内存中的 Collection 实例
        data_dir: 持久化根目录
    """

    def __init__(self, data_dir: str | None = None):
        """初始化 MemoryManager

        Args:
            data_dir: 数据存储目录，默认使用 get_default_data_dir()
        """
        self.logger = CustomLogger()
        self.collections: dict[str, UnifiedCollection] = {}
        self.data_dir = Path(data_dir) if data_dir else Path(get_default_data_dir())
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create_collection(
        self, name: str, config: dict[str, Any] | None = None
    ) -> UnifiedCollection:
        """创建新的 Collection

        Args:
            name: Collection 名称
            config: Collection 配置（可选）

        Returns:
            新创建的 UnifiedCollection 实例

        示例：
            >>> manager = MemoryManager()
            >>> collection = manager.create_collection("my_data", {"max_size": 1000})
        """
        if name in self.collections:
            self.logger.warning(f"Collection '{name}' already exists in memory")
            return self.collections[name]

        collection = UnifiedCollection(name, config or {})
        self.logger.info(f"Created collection '{name}'")
        return collection

    def get_collection(self, name: str) -> UnifiedCollection | None:
        """获取 Collection（支持懒加载）

        如果 Collection 在内存中，直接返回；
        否则尝试从磁盘加载。

        Args:
            name: Collection 名称

        Returns:
            Collection 实例，如果不存在返回 None

        示例：
            >>> manager = MemoryManager()
            >>> collection = manager.get_collection("my_data")  # 自动从磁盘加载
        """
        # 内存中存在
        if name in self.collections:
            return self.collections[name]

        # 尝试从磁盘加载
        if self.has_on_disk(name):
            self.logger.info(f"Lazy loading collection '{name}' from disk")
            return self.load_collection(name)

        return None

    def remove_collection(self, name: str) -> bool:
        """删除 Collection（内存 + 磁盘）

        Args:
            name: Collection 名称

        Returns:
            是否删除成功

        示例：
            >>> manager = MemoryManager()
            >>> manager.remove_collection("my_data")
        """
        # 从内存删除
        if name in self.collections:
            del self.collections[name]
            self.logger.info(f"Removed collection '{name}' from memory")

        # 从磁盘删除
        collection_path = self._get_collection_path(name)
        if collection_path.exists():
            shutil.rmtree(collection_path)
            self.logger.info(f"Removed collection '{name}' from disk")

        return True

    def persist(self, name: str) -> bool:
        """持久化 Collection 到磁盘

        Args:
            name: Collection 名称

        Returns:
            是否持久化成功

        示例：
            >>> manager = MemoryManager()
            >>> collection = manager.create_collection("my_data")
            >>> collection.insert("id1", {"text": "hello"})
            >>> manager.persist("my_data")
        """
        if name not in self.collections:
            self.logger.error(f"Collection '{name}' not found in memory")
            return False

        collection = self.collections[name]
        save_path = self._get_collection_path(name)
        save_path.mkdir(parents=True, exist_ok=True)

        try:
            # 保存原始数据
            with open(save_path / "raw_data.json", "w") as f:
                json.dump(collection.raw_data, f, indent=2, ensure_ascii=False)

            # 保存索引元信息
            with open(save_path / "index_metadata.json", "w") as f:
                json.dump(collection.index_metadata, f, indent=2, ensure_ascii=False)

            # 保存 Collection 配置
            with open(save_path / "config.json", "w") as f:
                json.dump(collection.config, f, indent=2)

            # 保存各个索引
            for idx_name, index in collection.indexes.items():
                index_path = save_path / f"index_{idx_name}"
                index.save(index_path)

            self.logger.info(
                f"Persisted collection '{name}' to {save_path} "
                f"({len(collection.raw_data)} items, {len(collection.indexes)} indexes)"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to persist collection '{name}': {e}")
            return False

    def load_collection(self, name: str) -> UnifiedCollection | None:
        """从磁盘加载 Collection

        Args:
            name: Collection 名称

        Returns:
            加载的 UnifiedCollection 实例，失败返回 None

        示例：
            >>> manager = MemoryManager()
            >>> collection = manager.load_collection("my_data")
        """
        load_path = self._get_collection_path(name)
        if not load_path.exists():
            self.logger.warning(f"Collection '{name}' not found on disk")
            return None

        try:
            # 加载配置
            config = {}
            config_path = load_path / "config.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)

            # 创建 Collection
            collection = UnifiedCollection(name, config)

            # 加载原始数据
            raw_data_path = load_path / "raw_data.json"
            if raw_data_path.exists():
                with open(raw_data_path) as f:
                    collection.raw_data = json.load(f)

            # 加载索引元信息
            metadata_path = load_path / "index_metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    collection.index_metadata = json.load(f)

            # 重建索引
            for idx_name, meta in collection.index_metadata.items():
                index_type = meta["type"]
                index_config = meta["config"]

                # 通过工厂创建索引
                index = IndexFactory.create(index_type, index_config)

                # 加载索引数据
                index_path = load_path / f"index_{idx_name}"
                if index_path.exists():
                    index.load(index_path)

                collection.indexes[idx_name] = index

            # 注册到内存
            self.collections[name] = collection

            self.logger.info(
                f"Loaded collection '{name}' from {load_path} "
                f"({len(collection.raw_data)} items, {len(collection.indexes)} indexes)"
            )
            return collection

        except Exception as e:
            self.logger.error(f"Failed to load collection '{name}': {e}")
            return None

    def has_on_disk(self, name: str) -> bool:
        """检查 Collection 是否在磁盘上存在

        Args:
            name: Collection 名称

        Returns:
            是否存在
        """
        collection_path = self._get_collection_path(name)
        return collection_path.exists() and (collection_path / "raw_data.json").exists()

    def list_collections(self) -> dict[str, str]:
        """列出所有 Collection（内存 + 磁盘）

        Returns:
            {name: status} 字典，status 为 "memory", "disk", 或 "both"

        示例：
            >>> manager = MemoryManager()
            >>> collections = manager.list_collections()
            >>> # {"my_data": "both", "temp": "memory", "backup": "disk"}
        """
        result = {}

        # 内存中的
        for name in self.collections:
            result[name] = "memory"

        # 磁盘上的
        if self.data_dir.exists():
            for item in self.data_dir.iterdir():
                if item.is_dir() and (item / "raw_data.json").exists():
                    name = item.name
                    if name in result:
                        result[name] = "both"
                    else:
                        result[name] = "disk"

        return result

    def _get_collection_path(self, name: str) -> Path:
        """获取 Collection 的持久化路径

        Args:
            name: Collection 名称

        Returns:
            持久化路径（目录）
        """
        return self.data_dir / name

    def __repr__(self) -> str:
        """字符串表示"""
        collections = self.list_collections()
        return (
            f"MemoryManager(data_dir={self.data_dir}, "
            f"collections={len(collections)}, "
            f"in_memory={sum(1 for s in collections.values() if 'memory' in s)})"
        )
