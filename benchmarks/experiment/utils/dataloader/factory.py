"""数据集加载器工厂

根据数据集名称创建对应的 DataLoader 适配器。

典型用法：
    >>> loader = DataLoaderFactory.create("locomo")
    >>> loader = DataLoaderFactory.create("conflict_resolution_v1")
"""

from __future__ import annotations

from benchmarks.experiment.utils.dataloader.base import BaseDataLoader


class DataLoaderFactory:
    """数据集加载器工厂

    集中管理所有数据集类型，提供统一的创建入口。

    支持的数据集：
        - locomo: Locomo 长轮对话数据集
        - longmemeval: LongMemEval 长期记忆评估数据集
        - conflict_resolution: MemAgentBench 冲突解决数据集
        - conflict_resolution_v1: 冲突解决数据集 V1 版本
        - conflict_resolution_v2: 冲突解决数据集 V2 版本

    典型用法：
        >>> loader = DataLoaderFactory.create("locomo")
        >>> turns = loader.get_turn("conv-26")
    """

    # 注册的数据集类型
    _DATASET_TYPES = {
        "locomo",
        "longmemeval",
        "conflict_resolution",
        "conflict_resolution_v1",
        "conflict_resolution_v2",
    }

    @classmethod
    def create(cls, dataset: str) -> BaseDataLoader:
        """根据数据集名称创建 DataLoader

        Args:
            dataset: 数据集名称，如 "locomo", "conflict_resolution_v1"

        Returns:
            对应的 DataLoader 适配器实例

        Raises:
            ValueError: 不支持的数据集类型
        """
        # 延迟导入，避免循环依赖
        from .adapters import (
            ConflictResolutionAdapter,
            LocomoAdapter,
            LongMemEvalAdapter,
        )

        if dataset == "locomo":
            return LocomoAdapter()

        if dataset == "longmemeval":
            return LongMemEvalAdapter()

        if dataset == "conflict_resolution":
            return ConflictResolutionAdapter()

        if dataset == "conflict_resolution_v1":
            return ConflictResolutionAdapter(version="v1")

        if dataset == "conflict_resolution_v2":
            return ConflictResolutionAdapter(version="v2")

        raise ValueError(f"不支持的数据集: {dataset}. 支持的数据集: {sorted(cls._DATASET_TYPES)}")

    @classmethod
    def list_datasets(cls) -> list[str]:
        """列出所有支持的数据集

        Returns:
            数据集名称列表
        """
        return sorted(cls._DATASET_TYPES)

    @classmethod
    def is_supported(cls, dataset: str) -> bool:
        """检查数据集是否支持

        Args:
            dataset: 数据集名称

        Returns:
            是否支持该数据集
        """
        return dataset in cls._DATASET_TYPES
