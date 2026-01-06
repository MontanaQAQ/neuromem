"""
Enhanced Memory Collections with Paper Features.

Provides VDB and Graph collections with paper-specific features:
- Triple storage (TiM)
- Link evolution (A-Mem)
- Note structure with keywords/tags/context (A-Mem)
- Ebbinghaus forgetting (MemoryBank)
- User Portrait (MemoryBank)
- Heat score migration (MemoryOS)
- Segment-Page architecture (MemoryOS)
- Long-term Personal Memory (MemoryOS)
- Three-tier storage (MemGPT)
- Token budget filtering (SCM)
- Conflict detection (Mem0)
- Phrase/Passage node distinction (HippoRAG)
- Graph-enhanced memory (Mem0g)
"""

from __future__ import annotations

from typing import ClassVar

from .base_collection import IndexType
from .graph_collection import GraphMemoryCollection
from .hybrid_collection import HybridCollection
from .paper_features import (
    GraphPaperFeaturesMixin,
    HeatMigrationMixin,
    HierarchicalPaperFeaturesMixin,
    PaperFeaturesMixin,
)
from .vdb_collection import VDBMemoryCollection


class VDBMemoryCollectionWithFeatures(
    PaperFeaturesMixin,
    HeatMigrationMixin,
    VDBMemoryCollection,
):
    """
    VDB Memory Collection with all paper features.

    Extends VDBMemoryCollection with:
    - Triple storage (TiM paper)
    - Ebbinghaus forgetting (MemoryBank paper)
    - Token budget filtering (SCM paper)
    - Conflict detection (Mem0 paper)
    - Heat score calculation (MemoryOS paper)

    Usage:
        >>> collection = VDBMemoryCollectionWithFeatures({"name": "my_collection"})
        >>> # Create index
        >>> collection.create_index({
        ...     "name": "main",
        ...     "dim": 768,
        ...     "backend_type": "FAISS"
        ... })
        >>>
        >>> # Insert with conflict check
        >>> result = collection.insert_with_conflict_check(
        ...     content="John's age is 25",
        ...     vector=embedding_vector,
        ...     index_name="main",
        ...     resolution="replace"
        ... )
        >>>
        >>> # Retrieve with token budget
        >>> results = collection.retrieve_with_budget(
        ...     query=query_vector,
        ...     index_name="main",
        ...     token_budget=2000
        ... )
        >>>
        >>> # Track access and apply forgetting
        >>> collection.update_access(item_id)
        >>> forgotten = collection.apply_forgetting()
    """

    # Inherit supported_index_types from VDBMemoryCollection
    supported_index_types: ClassVar[set[IndexType]] = VDBMemoryCollection.supported_index_types


class GraphMemoryCollectionWithFeatures(
    GraphPaperFeaturesMixin,
    HeatMigrationMixin,
    GraphMemoryCollection,
):
    """
    Graph Memory Collection with paper features.

    Extends GraphMemoryCollection with:
    - Note structure with keywords/tags/context (A-Mem paper)
    - Link evolution (A-Mem paper)
    - Ebbinghaus forgetting (MemoryBank paper)
    - Heat score calculation (MemoryOS paper)
    - Phrase/Passage node distinction (HippoRAG paper)
    - Graph-enhanced memory with entities/relations (Mem0g paper)

    Usage:
        >>> collection = GraphMemoryCollectionWithFeatures({"name": "my_graph"})
        >>> # Create index
        >>> collection.create_index({"name": "default"})
        >>>
        >>> # A-Mem: Add notes with structured fields
        >>> note_id = collection.insert_note(
        ...     content="Alice is a software engineer",
        ...     keywords=["Alice", "engineer"],
        ...     tags=["profession", "tech"],
        ...     context="User mentioned their job",
        ... )
        >>>
        >>> # HippoRAG: Add phrase and passage nodes
        >>> passage_id = collection.insert_passage_node(
        ...     passage="Alice works at Google as a senior engineer.",
        ...     vector=passage_vector,
        ... )
        >>> phrase_id = collection.insert_phrase_node(
        ...     phrase="Alice",
        ...     source_passage_id=passage_id,
        ...     vector=phrase_vector,
        ... )
        >>>
        >>> # Mem0g: Add entities and relations
        >>> entity_id = collection.add_entity(
        ...     name="Alice",
        ...     entity_type="PERSON",
        ...     vector=entity_vector,
        ... )
        >>> collection.add_relation(
        ...     source_id=entity_id,
        ...     relation_type="works_at",
        ...     target_id="google_entity_id",
        ... )
        >>>
        >>> # Track access and apply forgetting
        >>> collection.update_access(node_id)
        >>> forgotten = collection.apply_forgetting()
    """

    # Inherit supported_index_types from GraphMemoryCollection
    supported_index_types: ClassVar[set[IndexType]] = GraphMemoryCollection.supported_index_types


class HybridCollectionWithFeatures(
    HierarchicalPaperFeaturesMixin,
    HybridCollection,
):
    """
    Hybrid Memory Collection with hierarchical paper features.

    Extends HybridCollection with:
    - User Portrait (MemoryBank paper)
    - Three-tier storage: Working Context, FIFO, Recall (MemGPT paper)
    - Segment-Page architecture (MemoryOS paper)
    - Long-term Personal Memory (MemoryOS paper)
    - Heat-based migration (MemoryOS paper)

    Usage:
        >>> collection = HybridCollectionWithFeatures({"name": "my_hybrid"})
        >>>
        >>> # MemGPT: Three-tier storage
        >>> collection.set_working_fact("user_name", "Alice")
        >>> collection.push_message("user", "Hello, I'm Alice")
        >>> # When FIFO is full, messages auto-evict to recall
        >>> recalled = collection.search_recall("Alice")
        >>>
        >>> # MemoryBank: User Portrait
        >>> collection.update_user_portrait(
        ...     daily_personality={"2024-01-01": {"mood": "happy"}},
        ...     global_portrait={"interests": ["coding", "music"]},
        ... )
        >>> context = collection.get_portrait_context()
        >>>
        >>> # MemoryOS: Segment-Page
        >>> page_id = collection.add_page("Today we discussed project plans")
        >>> segment_id = collection.assign_page_to_segment(
        ...     page_id, page_embedding=embedding
        ... )
        >>>
        >>> # MemoryOS: LPM
        >>> collection.update_user_profile({"name": "Alice", "role": "developer"})
        >>> collection.add_user_knowledge("Prefers morning meetings")
        >>> persona_context = collection.get_persona_context()
    """

    # Inherit supported_index_types from HybridCollection
    supported_index_types: ClassVar[set[IndexType]] = HybridCollection.supported_index_types


# Aliases for convenience
EnhancedVDBCollection = VDBMemoryCollectionWithFeatures
EnhancedGraphCollection = GraphMemoryCollectionWithFeatures
EnhancedHybridCollection = HybridCollectionWithFeatures
