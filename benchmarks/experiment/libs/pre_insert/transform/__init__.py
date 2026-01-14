"""
PreInsert Transform Actions

转换型预处理 Actions，包括：
- segment_denoise: SeCom 语义分段 + 压缩去噪
- summarize: 文本摘要压缩
"""

from .segment_denoise import SegmentDenoiseAction
from .summarize import SummarizeAction

__all__ = [
    "SummarizeAction",
    "SegmentDenoiseAction",
]
