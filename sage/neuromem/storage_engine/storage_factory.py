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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.libs.vdb import VDBBackend


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
    """SageDB 向量数据库存储

    适合大规模向量数据的持久化和检索。

    架构说明
    --------
    ``SageDBStorage`` 是 neuromem 内部 ``StorageBackend`` 接口的具体实现。
    它通过 ``sage.libs.vdb.create_backend("sagedb", config)`` 获取向量数据库后端，
    而 ``sagedb`` 后端由 ``isage-vdb`` 包在自身 ``__init__`` 中注册到
    ``sage.libs.vdb`` 注册表。

    这样设计使得：

    - ``SageDBStorage``（L4 neuromem）依赖 ``sage.libs.vdb.VDBBackend``（L3 接口），
      而**不直接依赖**具体的 ``isage-vdb`` 包。
    - ``isage-vdb`` 在自身包中注册 ``SageVDBBackend``，通过注册表解耦两个 L4 同层包。

    配置参数
    --------
    dim : int
        向量维度（默认 768）
    index_type : str
        ANNS 索引类型（默认 ``"FLAT"``）
    metric : str
        距离度量（默认 ``"L2"``）
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化 SageDB 存储

        Args:
            config: SageDB 配置字典，支持 ``dim``、``index_type``、``metric`` 等键。

        Raises:
            ImportError: 如果 isage-vdb 包未安装（install: pip install isage-neuromem[sagedb]）
        """
        self.config = config or {}
        try:
            from sage.libs.vdb import create_backend
        except ImportError as exc:
            raise ImportError(
                "SageDBStorage requires 'isage-libs'. Install with: pip install isage-libs"
            ) from exc

        try:
            # Triggers sagevdb import which registers SageVDBBackend on first use.
            import sagevdb  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "SageDBStorage requires the 'isage-vdb' package. "
                "Install the optional extra: pip install isage-neuromem[sagedb] "
                "or: pip install isage-vdb"
            ) from exc

        # _vdb is typed against VDBBackend (L3 interface).
        self._vdb: VDBBackend = create_backend("sagedb", self.config)

    # --- StorageBackend contract ---

    def put(self, key: str, data: dict[str, Any]) -> bool:
        """向 SageDB 写入一条向量数据。

        data 中必须包含 ``vector`` 字段；可选包含 ``text`` 和 ``metadata``。
        """
        if "vector" not in data:
            raise ValueError("SageDBStorage.put() requires a 'vector' field in data")

        self._vdb.add(
            ids=[key],
            vectors=[data["vector"]],
            metadata=[{"text": data.get("text", ""), **data.get("metadata", {})}],
        )
        return True

    def get(self, key: str) -> dict[str, Any] | None:
        results = self._vdb.query(filter_metadata={"id": key}, top_k=1)
        return results[0] if results else None

    def delete(self, key: str) -> bool:
        return self._vdb.delete([key])

    def keys(self) -> list[str]:
        return self._vdb.get_all_ids()

    def clear(self) -> bool:
        return self._vdb.clear()

    def __len__(self) -> int:
        return self._vdb.count()


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
