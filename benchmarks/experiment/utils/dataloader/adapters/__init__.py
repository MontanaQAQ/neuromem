"""数据集适配器模块

包装外部 sage.data.sources 的 DataLoader，
实现 BaseDataLoader 统一接口。
"""

from .conflict_resolution_adapter import ConflictResolutionAdapter
from .locomo_adapter import LocomoAdapter
from .longmemeval_adapter import LongMemEvalAdapter

__all__ = [
    "LocomoAdapter",
    "LongMemEvalAdapter",
    "ConflictResolutionAdapter",
]
