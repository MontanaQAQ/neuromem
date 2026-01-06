"""Neuromem Service Factory - 适配 Kernel ServiceFactory 接口

这个工厂类将 neuromem 的 Service 包装成 Kernel 所需的 ServiceFactory 格式，
使得新的 Service 可以无缝集成到现有的 Pipeline 架构中。

设计:
- 包装 MemoryServiceRegistry.create() 调用
- 返回 ServiceFactory 实例（兼容 env.register_service_factory()）
- 自动创建 UnifiedCollection
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sage.kernel.runtime.factory.service_factory import ServiceFactory

if TYPE_CHECKING:
    pass

from ..memory_collection import UnifiedCollection
from .hierarchical import (  # noqa: F401
    LinknoteGraphService,
    PropertyGraphService,
    SemanticInvertedKnowledgeGraphService,
)

# 导入所有 Service 以触发注册
from .partitional import (  # noqa: F401
    FeatureQueueSegmentCombinationService,
    FeatureQueueSummaryCombinationService,
    FeatureQueueVectorstoreCombinationService,
    FeatureSummaryVectorStoreCombinationService,
    FIFOQueueService,
    InvertedVectorStoreCombinationService,
    LSHHashService,
    SegmentService,
)
from .registry import MemoryServiceRegistry


class NeuromemServiceFactory:
    """
    Neuromem Service 工厂类

    功能:
    1. 根据服务类型创建 neuromem Service
    2. 自动创建 UnifiedCollection
    3. 返回 ServiceFactory 包装器（兼容 Kernel）

    使用示例:
        # 在 YAML 配置中：
        services:
          register_memory_service: "partitional.fifo_queue"  # 新格式
          fifo_queue:
            max_size: 20

        # 在代码中：
        service_name = config.get("services.register_memory_service")
        factory = NeuromemServiceFactory.create(service_name, config)
        env.register_service_factory(service_name, factory)
    """

    @staticmethod
    def create(service_name: str, config: Any) -> ServiceFactory:
        """
        创建 neuromem Service 的 ServiceFactory

        Args:
            service_name: 服务名称（支持两种格式）
                - 完整格式: "partitional.fifo_queue", "hierarchical.linknote_graph"
                - 简短格式: "fifo_queue" (自动识别类型)
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例

        Raises:
            ValueError: 如果服务类型不支持

        Example:
            # 完整格式（推荐）
            factory = NeuromemServiceFactory.create("partitional.fifo_queue", config)

            # 简短格式（兼容）
            factory = NeuromemServiceFactory.create("fifo_queue", config)
        """
        # 提取服务类型（去掉命名空间前缀，只保留服务名）
        # "partitional.lsh_hash" -> "lsh_hash"
        # "hierarchical.linknote_graph" -> "linknote_graph"
        if "." in service_name:
            _, service_type = service_name.rsplit(".", 1)
        else:
            service_type = service_name

        # 验证服务是否已注册
        service_class = MemoryServiceRegistry.get_service_class(service_type)
        if service_class is None:
            registered = MemoryServiceRegistry.list_registered()
            raise ValueError(
                f"不支持的服务类型: {service_type}（来自 {service_name}）。"
                f"已注册的类型: {', '.join(registered)}"
            )

        # 从配置读取 Service 参数
        # services.lsh_hash (对应 services_type: "partitional.lsh_hash")
        service_config = config.get(f"services.{service_type}", {})

        # 创建一个代理Service类，在setup时才创建真正的neuromem Service
        class NeuromemServiceProxy:
            """
            Neuromem Service 的代理类

            Kernel会尝试直接实例化这个类，但我们延迟到setup()时才创建真正的neuromem Service。
            """

            def __init__(self, ctx=None):
                """初始化代理（Kernel会调用这个）"""
                self.ctx = ctx
                self._service_type = service_type
                self._service_config = service_config
                self._service_instance = None
                self._collection = None

            def setup(self):
                """创建 UnifiedCollection 和真正的 Service 实例"""
                # 1. 创建 UnifiedCollection
                self._collection = UnifiedCollection(name=self._service_type)

                # 2. 使用 Registry 创建 Service
                self._service_instance = MemoryServiceRegistry.create(
                    service_type=self._service_type,
                    collection=self._collection,
                    config=self._service_config,
                )

            def teardown(self):
                """清理资源"""
                if self._service_instance:
                    self._service_instance = None
                if self._collection:
                    self._collection = None

            # ===== 转发所有方法到真正的Service =====
            def insert(
                self,
                entry: str,
                vector: Any = None,
                metadata: dict[str, Any] | None = None,
                *,
                insert_mode: str = "passive",
                insert_params: dict | None = None,
            ) -> str:
                """转发insert到neuromem Service（统一旧接口）"""
                if not self._service_instance:
                    raise RuntimeError("Service not initialized. Call setup() first.")
                return self._service_instance.insert(
                    entry, vector, metadata, insert_mode=insert_mode, insert_params=insert_params
                )

            def retrieve(
                self,
                query: str | None = None,
                vector: Any = None,
                metadata: dict[str, Any] | None = None,
                top_k: int = 5,
                hints: dict[str, Any] | None = None,
                threshold: float | None = None,
                **kwargs: Any,
            ) -> list[dict[str, Any]]:
                """统一retrieve接口（兼容旧服务）"""
                if not self._service_instance:
                    raise RuntimeError("Service not initialized. Call setup() first.")
                return self._service_instance.retrieve(
                    query=query,
                    vector=vector,
                    metadata=metadata,
                    top_k=top_k,
                    hints=hints,
                    threshold=threshold,
                    **kwargs,
                )

            def update(self, data_id: str, **kwargs: Any) -> bool:
                if not self._service_instance:
                    raise RuntimeError("Service not initialized. Call setup() first.")
                return self._service_instance.update(data_id, **kwargs)

            def delete(self, entry_id: str) -> bool:
                """删除数据（统一使用 entry_id 参数名）"""
                if not self._service_instance:
                    raise RuntimeError("Service not initialized. Call setup() first.")
                return self._service_instance.delete(entry_id)

            def clear(self) -> None:
                if not self._service_instance:
                    raise RuntimeError("Service not initialized. Call setup() first.")
                self._service_instance.clear()

            def get_stats(self) -> dict[str, Any]:
                """获取统计信息（兼容旧Service接口）"""
                if not self._service_instance:
                    return {"service_type": self._service_type, "status": "not_initialized"}
                # neuromem Service可能没有get_stats，返回基本信息
                return {
                    "service_type": self._service_type,
                    "config": self._service_config,
                }

        # 返回 ServiceFactory（使用提取后的service_type作为名称）
        # 例如: "partitional.fifo_queue" -> 使用 "fifo_queue"
        return ServiceFactory(service_type, NeuromemServiceProxy)
