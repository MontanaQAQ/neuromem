"""
Partitional Services - 简单分区型记忆服务

本模块包含基于单个 Collection + 多个索引的简单分区型服务：

1. FIFOQueueService - FIFO队列服务 (短期记忆)
2. LSHHashService - LSH哈希去重服务
3. SegmentService - 分段存储服务
4. FeatureSummaryVectorStoreCombinationService - 特征+摘要+向量组合服务
5. InvertedVectorStoreCombinationService - 倒排+向量组合服务

设计原则:
- 单个 UnifiedCollection
- 多个索引组合
- 明确的检索策略
"""

from .feature_queue_segment_combination import FeatureQueueSegmentCombinationService
from .feature_queue_summary_combination import FeatureQueueSummaryCombinationService
from .feature_queue_vectorstore_combination import (
    FeatureQueueVectorstoreCombinationService,
)
from .feature_summary_vectorstore_combination import (
    FeatureSummaryVectorStoreCombinationService,
)
from .fifo_queue_service import FIFOQueueService
from .inverted_vectorstore_combination import InvertedVectorStoreCombinationService
from .lsh_hash_service import LSHHashService
from .segment_service import SegmentService

__all__ = [
    "FIFOQueueService",
    "LSHHashService",
    "SegmentService",
    "FeatureQueueSegmentCombinationService",
    "FeatureQueueSummaryCombinationService",
    "FeatureQueueVectorstoreCombinationService",
    "FeatureSummaryVectorStoreCombinationService",
    "InvertedVectorStoreCombinationService",
]
