"""UnifiedCollection with Paper Features

这个模块提供 UnifiedCollection 与各种 Paper Features Mixin 的组合。

替代 enhanced_collections.py 中的 legacy Collection 组合：
- VDBMemoryCollectionWithFeatures → UnifiedCollectionWithVDBFeatures
- GraphMemoryCollectionWithFeatures → UnifiedCollectionWithGraphFeatures
- HybridCollectionWithFeatures → UnifiedCollectionWithHybridFeatures

所有组合都基于 UnifiedCollection，通过动态索引配置实现不同的功能。

典型用法：
    >>> # VDB 特性（Triple/Forgetting/TokenBudget/Conflict）
    >>> collection = UnifiedCollectionWithVDBFeatures("my_vdb")
    >>> collection.create_index({
    ...     "name": "main",
    ...     "index_type": "faiss",
    ...     "dim": 768,
    ... })
    >>>
    >>> # Graph 特性（A-Mem/LinkEvolution/HippoRAG/Mem0g）
    >>> graph_coll = UnifiedCollectionWithGraphFeatures("my_graph")
    >>> graph_coll.create_index({
    ...     "name": "default",
    ...     "index_type": "graph",
    ... })
    >>>
    >>> # Hierarchical 特性（UserPortrait/MemGPT/SegmentPage/LPM）
    >>> hybrid_coll = UnifiedCollectionWithHybridFeatures("my_hybrid")
"""

from __future__ import annotations

from typing import Any

from .paper_features import (
    GraphPaperFeaturesMixin,
    HierarchicalPaperFeaturesMixin,
    PaperFeaturesMixin,
)
from .unified_collection import UnifiedCollection


class MetadataStorageAdapter:
    """Adapter for UnifiedCollection metadata storage to match legacy interface"""

    def __init__(self, unified_collection: UnifiedCollection):
        self.collection = unified_collection
        self._fields: set[str] = set()

    def get(self, item_id: str) -> dict[str, Any] | None:
        """Get metadata for an item"""
        data = self.collection.get(item_id)
        return data["metadata"] if data else None

    def store(self, item_id: str, metadata: dict[str, Any]) -> bool:
        """Store metadata for an item"""
        data = self.collection.get(item_id)
        if not data:
            return False
        data["metadata"] = metadata
        self.collection.storage.put(item_id, data)
        return True

    def has_field(self, field_name: str) -> bool:
        """Check if a field is registered"""
        return field_name in self._fields

    def add_field(self, field_name: str) -> None:
        """Register a new field"""
        self._fields.add(field_name)


class TextStorageAdapter:
    """Adapter for UnifiedCollection text storage to match legacy interface"""

    def __init__(self, unified_collection: UnifiedCollection):
        self.collection = unified_collection

    def get(self, item_id: str) -> str | None:
        """Get text for an item"""
        data = self.collection.get(item_id)
        return data["text"] if data else None

    def get_all_ids(self) -> list[str]:
        """Get all item IDs"""
        return list(self.collection.raw_data.keys())


class UnifiedCollectionWithVDBFeatures(
    PaperFeaturesMixin,
    UnifiedCollection,
):
    """UnifiedCollection with VDB-specific paper features

    继承自:
    - TripleStorageMixin: Triple 存储（TiM paper）
    - ForgettingMixin: Ebbinghaus 遗忘曲线（MemoryBank paper）
    - TokenBudgetMixin: Token 预算过滤（SCM paper）
    - ConflictDetectionMixin: 冲突检测（Mem0 paper）
    - UnifiedCollection: 统一集合抽象

    典型用法：
        >>> collection = UnifiedCollectionWithVDBFeatures("my_collection")
        >>>
        >>> # 创建 FAISS 索引
        >>> collection.create_index({
        ...     "name": "main",
        ...     "index_type": "faiss",
        ...     "dim": 768,
        ... })
        >>>
        >>> # 插入 Triple（TiM paper）
        >>> triple_id = collection.insert_triple(
        ...     query="What is the capital of France?",
        ...     passage="Paris is the capital of France.",
        ...     answer="Paris",
        ...     vector=embedding_vector,
        ...     index_name="main",
        ... )
        >>>
        >>> # 带冲突检测的插入（Mem0 paper）
        >>> result = collection.insert_with_conflict_check(
        ...     text="John's age is 25",
        ...     vector=embedding_vector,
        ...     index_name="main",
        ...     resolution="replace",  # 或 "keep_both"
        ... )
        >>>
        >>> # 带 Token 预算的检索（SCM paper）
        >>> results = collection.retrieve_with_budget(
        ...     query_vector=query_vector,
        ...     index_name="main",
        ...     token_budget=2000,
        ... )
        >>>
        >>> # 更新访问时间（Ebbinghaus 遗忘）
        >>> collection.update_access(item_id)
        >>>
        >>> # 应用遗忘曲线删除旧数据
        >>> forgotten_ids = collection.apply_forgetting()

    配置示例：
        >>> collection = UnifiedCollectionWithVDBFeatures(
        ...     name="advanced_vdb",
        ...     storage_backend="memory",  # 或 "redis", "sagedb"
        ...     storage_config={},
        ... )
    """

    def __init__(self, *args, **kwargs):
        """Initialize with storage adapters for Mixin compatibility"""
        super().__init__(*args, **kwargs)
        self.metadata_storage = MetadataStorageAdapter(self)
        self.text_storage = TextStorageAdapter(self)

    def get_metadata(self, item_id: str) -> dict[str, Any] | None:
        """Get metadata for an item (Mixin compatibility)"""
        return self.metadata_storage.get(item_id)

    def get_all_ids(self) -> list[str]:
        """Get all item IDs (Mixin compatibility)"""
        return self.text_storage.get_all_ids()

    def has_item(self, item_id: str) -> bool:
        """Check if item exists (Mixin compatibility)"""
        return self.get(item_id) is not None


class UnifiedCollectionWithGraphFeatures(
    GraphPaperFeaturesMixin,
    UnifiedCollection,
):
    """UnifiedCollection with Graph-specific paper features

    继承自:
    - AMemNoteMixin: Note 结构（A-Mem paper）
    - LinkEvolutionMixin: Link 演化（A-Mem paper）
    - ForgettingMixin: Ebbinghaus 遗忘曲线（MemoryBank paper）
    - HippoRAGMixin: Phrase/Passage 节点区分（HippoRAG paper）
    - Mem0gMixin: 图增强记忆（Mem0g paper）
    - UnifiedCollection: 统一集合抽象

    典型用法：
        >>> collection = UnifiedCollectionWithGraphFeatures("my_graph")
        >>>
        >>> # 创建图索引
        >>> collection.create_index({
        ...     "name": "default",
        ...     "index_type": "graph",
        ... })
        >>>
        >>> # A-Mem: 插入结构化 Note
        >>> note_id = collection.insert_note(
        ...     content="Alice is a software engineer",
        ...     keywords=["Alice", "engineer"],
        ...     tags=["profession", "tech"],
        ...     context="User mentioned their job",
        ...     index_name="default",
        ... )
        >>>
        >>> # A-Mem: 添加 Note 之间的链接
        >>> collection.add_note_link(
        ...     from_note_id=note_id,
        ...     to_note_id=another_note_id,
        ...     weight=0.8,
        ...     index_name="default",
        ... )
        >>>
        >>> # HippoRAG: 添加 Passage 和 Phrase 节点
        >>> passage_id = collection.insert_passage_node(
        ...     passage="Alice works at Google.",
        ...     vector=passage_vector,
        ...     index_name="default",
        ... )
        >>> phrase_id = collection.insert_phrase_node(
        ...     phrase="Alice",
        ...     source_passage_id=passage_id,
        ...     vector=phrase_vector,
        ...     index_name="default",
        ... )
        >>>
        >>> # Mem0g: 添加实体和关系
        >>> entity_id = collection.add_entity(
        ...     name="Alice",
        ...     entity_type="PERSON",
        ...     vector=entity_vector,
        ...     index_name="default",
        ... )
        >>> collection.add_relation(
        ...     source_id=entity_id,
        ...     relation_type="works_at",
        ...     target_id=google_entity_id,
        ...     index_name="default",
        ... )

    配置示例：
        >>> collection = UnifiedCollectionWithGraphFeatures(
        ...     name="knowledge_graph",
        ...     storage_backend="memory",
        ...     storage_config={},
        ... )
    """

    def __init__(self, *args, **kwargs):
        """Initialize with storage adapters for Mixin compatibility"""
        super().__init__(*args, **kwargs)
        self.metadata_storage = MetadataStorageAdapter(self)
        self.text_storage = TextStorageAdapter(self)

    def get_metadata(self, item_id: str) -> dict[str, Any] | None:
        """Get metadata for an item (Mixin compatibility)"""
        return self.metadata_storage.get(item_id)

    def get_all_ids(self) -> list[str]:
        """Get all item IDs (Mixin compatibility)"""
        return self.text_storage.get_all_ids()


class UnifiedCollectionWithHybridFeatures(
    HierarchicalPaperFeaturesMixin,
    UnifiedCollection,
):
    """UnifiedCollection with Hierarchical/Hybrid paper features

    继承自:
    - UserPortraitMixin: 用户画像（MemoryBank paper）
    - MemGPTStorageMixin: 三层存储（MemGPT paper）
    - SegmentPageMixin: Segment-Page 架构（MemoryOS paper）
    - LPMMixin: 长期个人记忆（MemoryOS paper）
    - HeatMigrationMixin: 基于热度的迁移（MemoryOS paper）
    - UnifiedCollection: 统一集合抽象

    典型用法：
        >>> collection = UnifiedCollectionWithHybridFeatures("my_hybrid")
        >>>
        >>> # MemGPT: 三层存储（Working Context/FIFO/Recall）
        >>> collection.set_working_fact("user_name", "Alice")
        >>> collection.push_message("user", "Hello, I'm Alice")
        >>> # 当 FIFO 满时，消息自动驱逐到 Recall
        >>> recalled = collection.search_recall("Alice")
        >>>
        >>> # MemoryBank: 用户画像
        >>> collection.update_user_portrait(
        ...     daily_personality={"2024-01-01": {"mood": "happy"}},
        ...     global_portrait={"interests": ["coding", "music"]},
        ... )
        >>> context = collection.get_portrait_context()
        >>>
        >>> # MemoryOS: Segment-Page 架构
        >>> page_id = collection.add_page("Today we discussed project plans")
        >>> segment_id = collection.assign_page_to_segment(
        ...     page_id,
        ...     page_embedding=embedding,
        ... )
        >>>
        >>> # MemoryOS: 长期个人记忆（LPM）
        >>> collection.update_user_profile({"name": "Alice", "role": "developer"})
        >>> collection.add_user_knowledge("Prefers morning meetings")
        >>> persona_context = collection.get_persona_context()
        >>>
        >>> # MemoryOS: 热度迁移
        >>> hot_items = collection.get_hot_items(threshold=0.7)
        >>> migrated = collection.migrate_by_heat()

    配置示例：
        >>> collection = UnifiedCollectionWithHybridFeatures(
        ...     name="hierarchical_memory",
        ...     storage_backend="memory",
        ...     storage_config={},
        ... )
    """

    def __init__(self, *args, **kwargs):
        """Initialize with storage adapters for Mixin compatibility"""
        super().__init__(*args, **kwargs)
        self.metadata_storage = MetadataStorageAdapter(self)
        self.text_storage = TextStorageAdapter(self)

    def get_metadata(self, item_id: str) -> dict[str, Any] | None:
        """Get metadata for an item (Mixin compatibility)"""
        return self.metadata_storage.get(item_id)

    def get_all_ids(self) -> list[str]:
        """Get all item IDs (Mixin compatibility)"""
        return self.text_storage.get_all_ids()


# 便利别名（与 enhanced_collections.py 保持一致）
EnhancedUnifiedVDBCollection = UnifiedCollectionWithVDBFeatures
EnhancedUnifiedGraphCollection = UnifiedCollectionWithGraphFeatures
EnhancedUnifiedHybridCollection = UnifiedCollectionWithHybridFeatures
