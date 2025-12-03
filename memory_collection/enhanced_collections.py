"""
Enhanced Memory Collections with Paper Features.

Provides VDB and Graph collections with paper-specific features:
- Triple storage (TiM)
- Link evolution (A-Mem)
- Ebbinghaus forgetting (MemoryBank)
- Heat score migration (MemoryOS)
- Token budget filtering (SCM)
- Conflict detection (Mem0)
"""

from __future__ import annotations

from typing import ClassVar

from .base_collection import IndexType
from .graph_collection import GraphMemoryCollection
from .paper_features import (
    GraphPaperFeaturesMixin,
    HeatMigrationMixin,
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
    - Link evolution (A-Mem paper)
    - Ebbinghaus forgetting (MemoryBank paper)
    - Heat score calculation (MemoryOS paper)

    Usage:
        >>> collection = GraphMemoryCollectionWithFeatures({"name": "my_graph"})
        >>> # Create index
        >>> collection.create_index({"name": "default"})
        >>>
        >>> # Add nodes with edges
        >>> collection.insert(
        ...     content="Alice is a software engineer",
        ...     index_names="default",
        ...     node_id="alice",
        ...     edges=[("bob", 0.8)]
        ... )
        >>>
        >>> # Evolve links based on similarity
        >>> updated = collection.evolve_links(
        ...     node_id="alice",
        ...     index_name="default",
        ...     decay_factor=0.95,
        ...     get_vector_func=get_node_vector,
        ...     find_similar_func=find_similar
        ... )
        >>>
        >>> # Track access and apply forgetting
        >>> collection.update_access(node_id)
        >>> forgotten = collection.apply_forgetting()
    """

    # Inherit supported_index_types from GraphMemoryCollection
    supported_index_types: ClassVar[set[IndexType]] = GraphMemoryCollection.supported_index_types


# Aliases for convenience
EnhancedVDBCollection = VDBMemoryCollectionWithFeatures
EnhancedGraphCollection = GraphMemoryCollectionWithFeatures
