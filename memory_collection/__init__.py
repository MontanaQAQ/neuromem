"""
Memory Collection Module - Core memory collection implementations

设计原则：
- Collection = 一份数据 (text_storage + metadata_storage) + 多种类型的索引
- 三种基础 Collection 类型：VDB、KV、Graph
- 组合型 Collection：HybridCollection（一份数据 + 多种类型索引）
- Service : Collection = 1 : 1

论文特性支持（Part 5）：
- Triple storage (TiM) - 三元组存储
- Link evolution (A-Mem) - 链接演化
- Ebbinghaus forgetting (MemoryBank) - 遗忘曲线
- Heat score migration (MemoryOS) - 热度迁移
- Token budget filtering (SCM) - Token 预算
- Conflict detection (Mem0) - 冲突检测
"""

# Re-export SimpleGraphIndex from search_engine for backward compatibility
from ..search_engine.graph_index import SimpleGraphIndex
from .base_collection import BaseMemoryCollection, IndexType

# Enhanced collections with paper features
from .enhanced_collections import (
    EnhancedGraphCollection,
    EnhancedVDBCollection,
    GraphMemoryCollectionWithFeatures,
    VDBMemoryCollectionWithFeatures,
)
from .graph_collection import GraphMemoryCollection
from .hybrid_collection import HybridCollection
from .kv_collection import KVMemoryCollection

# Paper feature utilities
from .paper_features import (
    # 5.6 Conflict Detection (Mem0)
    ConflictConfig,
    ConflictDetectionMixin,
    ConflictDetector,
    ConflictResult,
    # 5.3 Ebbinghaus Forgetting (MemoryBank)
    EbbinghausForgetting,
    EntityAttributeExtractor,
    ForgettingConfig,
    ForgettingMixin,
    # Combined Mixins
    GraphPaperFeaturesMixin,
    # 5.4 Heat Score Migration (MemoryOS)
    HeatConfig,
    HeatMigrationMixin,
    HeatScoreManager,
    # 5.2 Link Evolution (A-Mem)
    LinkEvolutionMixin,
    PaperFeaturesMixin,
    # 5.5 Token Budget (SCM)
    SimpleTokenCounter,
    TiktokenCounter,
    TokenBudgetConfig,
    TokenBudgetFilter,
    TokenBudgetMixin,
    # 5.1 Triple Storage (TiM)
    Triple,
    TripleStorageMixin,
)
from .vdb_collection import VDBMemoryCollection

__all__ = [
    # Base classes
    "BaseMemoryCollection",
    "IndexType",
    # Basic collections
    "VDBMemoryCollection",
    "KVMemoryCollection",
    "GraphMemoryCollection",
    "HybridCollection",
    # Enhanced collections with paper features
    "VDBMemoryCollectionWithFeatures",
    "GraphMemoryCollectionWithFeatures",
    "EnhancedVDBCollection",
    "EnhancedGraphCollection",
    # Paper feature utilities - 5.1 Triple Storage
    "Triple",
    "TripleStorageMixin",
    # Paper feature utilities - 5.2 Link Evolution
    "LinkEvolutionMixin",
    # Paper feature utilities - 5.3 Forgetting
    "EbbinghausForgetting",
    "ForgettingConfig",
    "ForgettingMixin",
    # Paper feature utilities - 5.4 Heat Score
    "HeatConfig",
    "HeatScoreManager",
    "HeatMigrationMixin",
    # Paper feature utilities - 5.5 Token Budget
    "TokenBudgetConfig",
    "TokenBudgetFilter",
    "TokenBudgetMixin",
    "SimpleTokenCounter",
    "TiktokenCounter",
    # Paper feature utilities - 5.6 Conflict Detection
    "ConflictConfig",
    "ConflictDetector",
    "ConflictResult",
    "ConflictDetectionMixin",
    "EntityAttributeExtractor",
    # Combined Mixins
    "PaperFeaturesMixin",
    "GraphPaperFeaturesMixin",
    # Backward compatibility
    "SimpleGraphIndex",
]
