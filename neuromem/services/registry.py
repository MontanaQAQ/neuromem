"""
MemoryServiceRegistry - Service 工厂注册表

设计要点:
1. 工厂模式: 通过 service_type 创建 Service 实例
2. 注册机制: 装饰器注册新 Service
3. 延迟加载: 避免循环导入

核心方法:
- register(service_type, service_class): 注册 Service 类
- create(service_type, collection, config): 创建 Service 实例
- list_registered(): 列出所有已注册的 Service
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..memory_collection import UnifiedCollection
    from .base_service import BaseMemoryService

logger = logging.getLogger(__name__)


class MemoryServiceRegistry:
    """
    MemoryService 工厂注册表

    使用场景:
    1. 注册 Service 类:
        @MemoryServiceRegistry.register("fifo_queue")
        class FIFOQueueService(BaseMemoryService):
            ...

    2. 创建 Service 实例:
        service = MemoryServiceRegistry.create(
            "fifo_queue",
            collection=my_collection,
            config={"max_size": 10}
        )

    3. 列出已注册的 Service:
        services = MemoryServiceRegistry.list_registered()
        # ["fifo_queue", "lsh_hash", ...]
    """

    # 类变量：存储 service_type -> service_class 映射
    _registry: dict[str, type[BaseMemoryService]] = {}

    @classmethod
    def register(cls, service_type: str) -> Any:
        """
        注册 Service 类 (装饰器)

        Args:
            service_type: Service 类型标识符 (如 "fifo_queue", "lsh_hash")

        Returns:
            装饰器函数

        Example:
            @MemoryServiceRegistry.register("fifo_queue")
            class FIFOQueueService(BaseMemoryService):
                def _setup_indexes(self):
                    self.collection.add_index("queue", "fifo", {"max_size": 10})

        Note:
            - service_type 应使用小写字母 + 下划线 (如 "fifo_queue")
            - 重复注册会覆盖旧的类定义 (会打印警告)
        """

        def decorator(service_class: type[BaseMemoryService]) -> type[BaseMemoryService]:
            if service_type in cls._registry:
                logger.warning(
                    f"Service '{service_type}' already registered, "
                    f"overwriting with {service_class.__name__}"
                )
            cls._registry[service_type] = service_class
            logger.debug(f"Registered Service: '{service_type}' -> {service_class.__name__}")
            return service_class

        return decorator

    @classmethod
    def create(
        cls,
        service_type: str,
        collection: UnifiedCollection,
        config: dict[str, Any] | None = None,
    ) -> BaseMemoryService:
        """
        创建 Service 实例

        Args:
            service_type: Service 类型 (必须已注册)
            collection: UnifiedCollection 实例
            config: Service 配置字典

        Returns:
            Service 实例

        Raises:
            ValueError: 如果 service_type 未注册

        Example:
            from neuromem import UnifiedCollection, MemoryServiceRegistry

            # 创建 Collection
            collection = UnifiedCollection("my_collection")

            # 创建 Service
            service = MemoryServiceRegistry.create(
                "fifo_queue",
                collection=collection,
                config={"max_size": 10}
            )

            # 使用 Service
            data_id = service.insert("Hello, world!")
            results = service.retrieve("world", top_k=5)
        """
        if service_type not in cls._registry:
            raise ValueError(
                f"Service type '{service_type}' not registered. "
                f"Available: {list(cls._registry.keys())}"
            )

        service_class = cls._registry[service_type]
        logger.info(f"Creating {service_class.__name__} for collection '{collection.name}'")
        return service_class(collection, config)

    @classmethod
    def list_registered(cls) -> list[str]:
        """
        列出所有已注册的 Service 类型

        Returns:
            Service 类型列表

        Example:
            >>> MemoryServiceRegistry.list_registered()
            ['fifo_queue', 'lsh_hash', 'segment', ...]
        """
        return list(cls._registry.keys())

    @classmethod
    def get_service_class(cls, service_type: str) -> type[BaseMemoryService] | None:
        """
        获取 Service 类 (不创建实例)

        Args:
            service_type: Service 类型

        Returns:
            Service 类或 None

        Note:
            - 用于高级用例，如自定义实例化逻辑
            - 一般情况直接使用 create() 即可
        """
        return cls._registry.get(service_type)
