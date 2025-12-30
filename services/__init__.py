"""
MemoryService 层 - 基于 UnifiedCollection 的业务逻辑实现

设计原则:
- Service = Collection + 业务逻辑
- Service 组合 UnifiedCollection (不继承)
- 统一的抽象接口 (BaseMemoryService)
- 工厂模式注册 (MemoryServiceRegistry)

模块结构:
- base_service.py: BaseMemoryService 抽象基类
- registry.py: MemoryServiceRegistry 服务注册表
- neuromem_service_factory.py: Kernel ServiceFactory 适配器
- partitional/: 简单分区型服务 (FIFO, LSH, Segment, etc.)
- hierarchical/: 层次型服务 (SemanticKG, Linknote, PropertyGraph)
"""

from .base_service import BaseMemoryService
from .neuromem_service_factory import NeuromemServiceFactory
from .registry import MemoryServiceRegistry

__all__ = ["BaseMemoryService", "MemoryServiceRegistry", "NeuromemServiceFactory"]
