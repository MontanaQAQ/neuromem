"""统一数据集加载器模块

提供对多种数据集的统一抽象，解耦外部依赖。

核心组件：
- BaseDataLoader: 抽象基类，定义统一接口
- DataLoaderFactory: 工厂类，根据数据集名称创建加载器
- 各 Adapter: 适配器，包装外部 DataLoader

典型用法：
    >>> from benchmarks.experiment.utils.dataloader import DataLoaderFactory
    >>> loader = DataLoaderFactory.create("locomo")
    >>> turns = loader.get_turn("conv-26")
"""

from .base import BaseDataLoader
from .factory import DataLoaderFactory

__all__ = [
    "BaseDataLoader",
    "DataLoaderFactory",
]
