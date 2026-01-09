"""
Storage Factory - 可插拔存储后端

提供统一的存储抽象，支持多种后端：
- Memory: 内存存储（默认）
- Redis: Redis 持久化存储
- SageDB: 向量数据库存储

设计原则：
- 所有后端实现统一接口 (StorageBackend)
- Collection 通过工厂创建存储实例
- 支持配置化切换后端
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """
    存储后端抽象接口

    所有存储后端必须实现的方法：
    - put: 存储数据
    - get: 获取数据
    - delete: 删除数据
    - keys: 获取所有键
    - clear: 清空所有数据
    """

    @abstractmethod
    def put(self, key: str, data: dict[str, Any]) -> bool:
        """
        存储数据

        Args:
            key: 数据唯一标识
            data: 数据字典，必须包含 text 和 metadata

        Returns:
            是否存储成功
        """

    @abstractmethod
    def get(self, key: str) -> dict[str, Any] | None:
        """
        获取数据

        Args:
            key: 数据唯一标识

        Returns:
            数据字典或 None（不存在）
        """

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        删除数据

        Args:
            key: 数据唯一标识

        Returns:
            是否删除成功
        """

    @abstractmethod
    def keys(self) -> list[str]:
        """
        获取所有键

        Returns:
            所有数据 ID 列表
        """

    @abstractmethod
    def clear(self) -> bool:
        """
        清空所有数据

        Returns:
            是否清空成功
        """

    @abstractmethod
    def __len__(self) -> int:
        """返回数据数量"""


class MemoryStorage(StorageBackend):
    """
    内存存储（默认）

    数据存储在内存字典中，速度快但不持久化。
    适合开发测试和小规模应用。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化内存存储

        Args:
            config: 配置字典（当前未使用，为将来扩展预留）
        """
        self.config = config or {}
        self.data: dict[str, dict[str, Any]] = {}

    def put(self, key: str, data: dict[str, Any]) -> bool:
        self.data[key] = data
        return True

    def get(self, key: str) -> dict[str, Any] | None:
        return self.data.get(key)

    def delete(self, key: str) -> bool:
        if key in self.data:
            del self.data[key]
            return True
        return False

    def keys(self) -> list[str]:
        return list(self.data.keys())

    def clear(self) -> bool:
        self.data.clear()
        return True

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        """使 MemoryStorage 可迭代，返回所有键"""
        return iter(self.data.keys())


class RedisStorage(StorageBackend):
    """
    Redis 存储

    将数据持久化到 Redis，适合分布式场景。

    配置参数:
        host: Redis 主机地址（默认 localhost）
        port: Redis 端口（默认 6379）
        db: Redis 数据库编号（默认 0）
        password: Redis 密码（可选）
        prefix: 键前缀（默认 "neuromem:"）
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化 Redis 存储

        Args:
            config: Redis 配置字典

        Raises:
            ImportError: 如果 redis 包未安装
        """
        try:
            import redis
        except ImportError as e:
            raise ImportError(
                "redis package is required for RedisStorage. Install it with: pip install redis"
            ) from e

        self.config = config or {}
        self.prefix = self.config.get("prefix", "neuromem:")

        self.redis = redis.Redis(
            host=self.config.get("host", "localhost"),
            port=self.config.get("port", 6379),
            db=self.config.get("db", 0),
            password=self.config.get("password"),
            decode_responses=True,  # 自动解码为字符串
        )

    def _make_key(self, key: str) -> str:
        """添加前缀到键"""
        return f"{self.prefix}{key}"

    def put(self, key: str, data: dict[str, Any]) -> bool:
        import json

        redis_key = self._make_key(key)
        self.redis.set(redis_key, json.dumps(data, ensure_ascii=False))
        return True

    def get(self, key: str) -> dict[str, Any] | None:
        import json

        redis_key = self._make_key(key)
        value = self.redis.get(redis_key)
        return json.loads(value) if value else None

    def delete(self, key: str) -> bool:
        redis_key = self._make_key(key)
        return bool(self.redis.delete(redis_key))

    def keys(self) -> list[str]:
        pattern = f"{self.prefix}*"
        redis_keys = self.redis.keys(pattern)
        # 去掉前缀
        prefix_len = len(self.prefix)
        return [k[prefix_len:] for k in redis_keys]

    def clear(self) -> bool:
        pattern = f"{self.prefix}*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
        return True

    def __len__(self) -> int:
        pattern = f"{self.prefix}*"
        return len(self.redis.keys(pattern))


class SageDBStorage(StorageBackend):
    """
    SageDB 向量数据库存储

    适合大规模向量数据的持久化和检索。

    配置参数:
        db_path: 数据库路径（默认 ./sagedb_data）
        dim: 向量维度（默认 768）
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化 SageDB 存储

        Args:
            config: SageDB 配置字典

        Raises:
            ImportError: 如果 sagedb 包未安装
        """
        try:
            from sagedb import SageDB
        except ImportError as e:
            raise ImportError(
                "sagedb package is required for SageDBStorage. Install it with: pip install isage-vdb"
            ) from e

        self.config = config or {}
        self.sagedb = SageDB(
            db_path=self.config.get("db_path", "./sagedb_data"),
            dim=self.config.get("dim", 768),
        )

    def put(self, key: str, data: dict[str, Any]) -> bool:
        # SageDB 需要向量，如果数据中没有向量则无法存储
        # 这里假设 data 中有 "vector" 字段
        if "vector" not in data:
            raise ValueError("SageDBStorage requires 'vector' field in data")

        self.sagedb.add(
            ids=[key],
            vectors=[data["vector"]],
            metadata=[{"text": data.get("text", ""), **data.get("metadata", {})}],
        )
        return True

    def get(self, key: str) -> dict[str, Any] | None:
        # SageDB 不支持直接通过 ID 获取，需要通过查询
        # 这里使用元数据查询
        results = self.sagedb.query(filter_metadata={"id": key}, top_k=1)
        if results and len(results) > 0:
            return results[0]
        return None

    def delete(self, key: str) -> bool:
        # SageDB 删除功能（如果支持）
        if hasattr(self.sagedb, "delete"):
            self.sagedb.delete([key])
            return True
        return False

    def keys(self) -> list[str]:
        # SageDB 获取所有 ID（如果支持）
        if hasattr(self.sagedb, "get_all_ids"):
            return self.sagedb.get_all_ids()
        return []

    def clear(self) -> bool:
        # SageDB 清空数据（如果支持）
        if hasattr(self.sagedb, "clear"):
            self.sagedb.clear()
            return True
        return False

    def __len__(self) -> int:
        # SageDB 获取数据量
        if hasattr(self.sagedb, "count"):
            return self.sagedb.count()
        return len(self.keys())


class StorageFactory:
    """
    存储后端工厂

    用于创建不同类型的存储后端实例。

    支持的后端:
        - memory: 内存存储（默认）
        - redis: Redis 存储
        - sagedb: SageDB 向量数据库

    使用示例:
        >>> storage = StorageFactory.create("memory")
        >>> storage = StorageFactory.create("redis", {"host": "localhost"})
    """

    _backends: dict[str, type[StorageBackend]] = {
        "memory": MemoryStorage,
        "redis": RedisStorage,
        "sagedb": SageDBStorage,
    }

    @classmethod
    def create(cls, backend: str, config: dict[str, Any] | None = None) -> StorageBackend:
        """
        创建存储后端实例

        Args:
            backend: 后端类型 ("memory", "redis", "sagedb")
            config: 后端配置字典

        Returns:
            StorageBackend 实例

        Raises:
            ValueError: 如果后端类型未知
        """
        if backend not in cls._backends:
            available = ", ".join(cls._backends.keys())
            raise ValueError(f"Unknown storage backend '{backend}'. Available: {available}")

        backend_class = cls._backends[backend]
        return backend_class(config)

    @classmethod
    def register(cls, name: str, backend_class: type[StorageBackend]) -> None:
        """
        注册自定义存储后端

        Args:
            name: 后端名称
            backend_class: 实现 StorageBackend 接口的类
        """
        cls._backends[name] = backend_class
