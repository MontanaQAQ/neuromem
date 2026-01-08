"""
Memory Collection Module - 统一数据容器

v0.2.1+ 架构更新:
- 推荐使用 UnifiedCollection（统一实现）
- 支持可插拔存储后端（Memory/Redis/SageDB）
- 旧 Collection 类已删除

迁移指南: docs/dev-note/MIGRATION_GUIDE.md
API参考: docs/COLLECTION_CONFIG_GUIDE.md
"""

# Paper feature utilities (Mixins and helper classes)
from .paper_features import (
    AgentPersona,
    # 5.0 A-Mem Note Structure
    AMemNote,
    AMemNoteMixin,
    # 5.6 Conflict detection (Mem0)
    ConflictConfig,
    ConflictDetectionMixin,
    ConflictDetector,
    ConflictResult,
    # 5.3 Ebbinghaus Forgetting (MemoryBank)
    EbbinghausForgetting,
    EdgeType,
    EntityAttributeExtractor,
    ForgettingConfig,
    ForgettingMixin,
    GraphPaperFeaturesMixin,
    # 5.4 Heat Score Migration (MemoryOS)
    HeatConfig,
    HeatMigrationMixin,
    HeatScoreManager,
    HierarchicalPaperFeaturesMixin,
    # 5.7 HippoRAG Node Types
    HippoRAGMixin,
    HippoRAGNode,
    # 5.2 Link Evolution (A-Mem)
    LinkEvolutionMixin,
    # 5.4.3 LPM (MemoryOS)
    LPMMixin,
    Mem0gEntity,
    # 5.8 Mem0g Graph-Enhanced
    Mem0gMixin,
    Mem0gRelation,
    MemGPTMessage,
    # 5.4.1 MemGPT Three-Tier Storage
    MemGPTStorageMixin,
    MemGPTWorkingContext,
    MemoryOSLPM,
    MemoryOSPage,
    MemoryOSSegment,
    NodeType,
    # Combined Mixins
    PaperFeaturesMixin,
    # 5.4.2 Segment-Page architecture (MemoryOS)
    SegmentPageMixin,
    SimpleTokenCounter,
    TiktokenCounter,
    # 5.5 Token Budget filtering (SCM)
    TokenBudgetConfig,
    TokenBudgetFilter,
    TokenBudgetMixin,
    # 5.1 Triple Storage (TiM)
    Triple,
    TripleStorageMixin,
    UserPersona,
    # 5.3.1 User Portrait (MemoryBank)
    UserPortrait,
    UserPortraitMixin,
)
from .unified_collection import UnifiedCollection

__all__ = [
    # Core
    "UnifiedCollection",
    # Paper feature utilities - 5.0 A-Mem Note
    "AMemNote",
    "AMemNoteMixin",
    # Paper feature utilities - 5.1 Triple Storage
    "Triple",
    "TripleStorageMixin",
    # Paper feature utilities - 5.2 Link Evolution
    "LinkEvolutionMixin",
    # Paper feature utilities - 5.3 Forgetting
    "EbbinghausForgetting",
    "ForgettingConfig",
    "ForgettingMixin",
    # Paper feature utilities - 5.3.1 User Portrait
    "UserPortrait",
    "UserPortraitMixin",
    # Paper feature utilities - 5.4 Heat Score
    "HeatConfig",
    "HeatScoreManager",
    "HeatMigrationMixin",
    # Paper feature utilities - 5.4.1 MemGPT Three-Tier
    "MemGPTStorageMixin",
    "MemGPTWorkingContext",
    "MemGPTMessage",
    # Paper feature utilities - 5.4.2 Segment-Page
    "SegmentPageMixin",
    "MemoryOSSegment",
    "MemoryOSPage",
    # Paper feature utilities - 5.4.3 LPM
    "LPMMixin",
    "MemoryOSLPM",
    "UserPersona",
    "AgentPersona",
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
    # Paper feature utilities - 5.7 HippoRAG
    "HippoRAGMixin",
    "HippoRAGNode",
    "NodeType",
    "EdgeType",
    # Paper feature utilities - 5.8 Mem0g
    "Mem0gMixin",
    "Mem0gEntity",
    "Mem0gRelation",
    # Combined Mixins
    "PaperFeaturesMixin",
    "GraphPaperFeaturesMixin",
    "HierarchicalPaperFeaturesMixin",
]
