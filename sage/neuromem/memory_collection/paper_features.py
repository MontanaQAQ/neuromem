"""
Paper-specific features for NeuroMem Collections.

This module implements features from various memory-augmented LLM papers:
- TiM: Triple storage (query, passage, answer)
- A-Mem: Link evolution based on similarity, Note structure with keywords/tags/context
- MemoryBank: Ebbinghaus forgetting curve, User Portrait
- MemGPT: Three-tier storage with recall persistence
- MemoryOS: Heat score based tier migration, Segment-Page architecture, LPM
- SCM: Token budget filtering
- Mem0: Conflict detection
- Mem0g: Graph-enhanced version with labeled directed graph
- HippoRAG: Phrase/Passage node distinction

These are designed as composable utilities that can be used with any Collection.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# 5.0 A-Mem Note Structure
# =============================================================================


@dataclass
class AMemNote:
    """
    A-Mem Note structure (A-MEM: Agentic Memory for LLM Agents).

    Each note contains:
    - content: Original content ci
    - timestamp: Creation time ti
    - keywords: LLM-generated keywords Ki
    - tags: LLM-generated tags Gi
    - context: LLM-generated contextual description Xi
    - embedding: Embedding vector ei
    - links: Set of linked note IDs Li
    """

    note_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    context: str = ""
    embedding: np.ndarray | None = None
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert note to dictionary for storage."""
        return {
            "note_id": self.note_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "keywords": self.keywords,
            "tags": self.tags,
            "context": self.context,
            "links": self.links,
            "metadata": self.metadata,
            # embedding is stored separately in VDB index
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], embedding: np.ndarray | None = None) -> AMemNote:
        """Create note from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            from datetime import timezone

            timestamp = datetime.now(timezone.utc)

        return cls(
            note_id=data.get("note_id", str(uuid4())),
            content=data.get("content", ""),
            timestamp=timestamp,
            keywords=data.get("keywords", []),
            tags=data.get("tags", []),
            context=data.get("context", ""),
            embedding=embedding,
            links=data.get("links", []),
            metadata=data.get("metadata", {}),
        )

    def to_metadata(self) -> dict[str, Any]:
        """Convert note fields to metadata format for storage."""
        return {
            "note_type": "amem",
            "keywords": self.keywords,
            "tags": self.tags,
            "context": self.context,
            "links": self.links,
            "timestamp": self.timestamp.isoformat(),
            **self.metadata,
        }


class AMemNoteMixin:
    """
    Mixin for GraphMemoryCollection to support A-Mem Note structure.

    Provides methods for:
    - Inserting notes with keywords/tags/context
    - Updating note fields (Memory Evolution)
    - Managing links between notes (Link Evolution)
    """

    def insert_note(
        self,
        content: str,
        keywords: list[str] | None = None,
        tags: list[str] | None = None,
        context: str = "",
        vector: np.ndarray | None = None,
        index_name: str = "default",
        note_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Insert an A-Mem note with structured fields.

        Args:
            content: Note content
            keywords: LLM-generated keywords
            tags: LLM-generated tags
            context: Contextual description
            vector: Embedding vector
            index_name: Target index name
            note_id: Optional note ID (auto-generated if None)
            **kwargs: Additional metadata

        Returns:
            Note ID
        """
        note = AMemNote(
            note_id=note_id or str(uuid4()),
            content=content,
            keywords=keywords or [],
            tags=tags or [],
            context=context,
            embedding=vector,
            metadata=kwargs,
        )

        # Use parent class insert method
        return self.insert(  # type: ignore[attr-defined]
            content=content,
            index_names=index_name,
            vector=vector,
            metadata=note.to_metadata(),
            node_id=note.note_id,
        )

    def update_note_fields(
        self,
        note_id: str,
        keywords: list[str] | None = None,
        tags: list[str] | None = None,
        context: str | None = None,
        links: list[str] | None = None,
    ) -> bool:
        """
        Update note fields (Memory Evolution).

        Args:
            note_id: Note ID to update
            keywords: New keywords (None = keep existing)
            tags: New tags (None = keep existing)
            context: New context (None = keep existing)
            links: New links (None = keep existing)

        Returns:
            True if updated successfully
        """
        if not hasattr(self, "metadata_storage"):
            return False

        metadata = self.metadata_storage.get(note_id)  # type: ignore[attr-defined]
        if metadata is None:
            return False

        # Update fields
        if keywords is not None:
            metadata["keywords"] = keywords
        if tags is not None:
            metadata["tags"] = tags
        if context is not None:
            metadata["context"] = context
        if links is not None:
            metadata["links"] = links

        # Ensure fields are registered
        for field_name in ["keywords", "tags", "context", "links"]:
            if not self.metadata_storage.has_field(field_name):  # type: ignore[attr-defined]
                self.metadata_storage.add_field(field_name)  # type: ignore[attr-defined]

        self.metadata_storage.store(note_id, metadata)  # type: ignore[attr-defined]
        return True

    def get_note(self, note_id: str) -> AMemNote | None:
        """
        Retrieve a note by ID.

        Args:
            note_id: Note ID

        Returns:
            AMemNote or None if not found
        """
        if not hasattr(self, "text_storage") or not hasattr(self, "metadata_storage"):
            return None

        content = self.text_storage.get(note_id)  # type: ignore[attr-defined]
        if content is None:
            return None

        metadata = self.metadata_storage.get(note_id) or {}  # type: ignore[attr-defined]

        timestamp_str = metadata.get("timestamp")
        from datetime import timezone

        timestamp = (
            datetime.fromisoformat(timestamp_str)
            if isinstance(timestamp_str, str)
            else datetime.now(timezone.utc)
        )

        return AMemNote(
            note_id=note_id,
            content=content,
            timestamp=timestamp,
            keywords=metadata.get("keywords", []),
            tags=metadata.get("tags", []),
            context=metadata.get("context", ""),
            links=metadata.get("links", []),
            metadata={
                k: v
                for k, v in metadata.items()
                if k not in ["keywords", "tags", "context", "links", "timestamp", "note_type"]
            },
        )

    def add_note_link(
        self,
        from_note_id: str,
        to_note_id: str,
        weight: float = 1.0,
        index_name: str = "default",
    ) -> bool:
        """
        Add a link between two notes.

        Args:
            from_note_id: Source note ID
            to_note_id: Target note ID
            weight: Link weight
            index_name: Graph index name

        Returns:
            True if link added successfully
        """
        # Update links in metadata
        metadata = self.metadata_storage.get(from_note_id)  # type: ignore[attr-defined]
        if metadata is None:
            return False

        links = metadata.get("links", [])
        if to_note_id not in links:
            links.append(to_note_id)
            metadata["links"] = links
            self.metadata_storage.store(from_note_id, metadata)  # type: ignore[attr-defined]

        # Add edge in graph index
        if hasattr(self, "add_edge"):
            self.add_edge(from_note_id, to_note_id, weight, index_name)  # type: ignore[attr-defined]

        return True


# =============================================================================
# 5.1 Triple Storage (TiM)
# =============================================================================


@dataclass
class Triple:
    """A triple consisting of query, passage, and answer."""

    query: str
    passage: str
    answer: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(
            {
                "query": self.query,
                "passage": self.passage,
                "answer": self.answer,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, json_str: str) -> Triple:
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(
            query=data["query"],
            passage=data["passage"],
            answer=data["answer"],
        )

    def get_query_hash(self) -> str:
        """Get MD5 hash of query (first 8 chars)."""
        return hashlib.md5(self.query.encode()).hexdigest()[:8]

    def get_passage_hash(self) -> str:
        """Get MD5 hash of passage (first 8 chars)."""
        return hashlib.md5(self.passage.encode()).hexdigest()[:8]


class TripleStorageMixin:
    """
    Mixin for VDBMemoryCollection to support triple storage (TiM paper).

    Stores (query, passage, answer) triples with vector indexing based on passage.
    """

    def insert_triple(
        self,
        query: str,
        passage: str,
        answer: str,
        vector: np.ndarray | None = None,
        index_name: str = "triple_index",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Insert a triple into the collection.

        Args:
            query: The query text
            passage: The passage text (used for embedding)
            answer: The answer text
            vector: Pre-computed embedding vector (optional for UnifiedCollection)
            index_name: Name of the index to insert into
            metadata: Optional additional metadata

        Returns:
            stable_id of the inserted triple
        """
        triple = Triple(query=query, passage=passage, answer=answer)
        content = triple.to_json()

        extended_metadata = {
            **(metadata or {}),
            "type": "triple",
            "query_hash": triple.get_query_hash(),
            "passage_hash": triple.get_passage_hash(),
        }

        # Use the parent class insert method
        # Support both legacy Collection (content=) and UnifiedCollection (text=)
        if hasattr(self, "_is_unified_collection"):
            return self.insert(  # type: ignore[attr-defined]
                text=content,
                metadata=extended_metadata,
                index_names=[index_name] if isinstance(index_name, str) else index_name,
            )
        # Legacy Collection interface
        return self.insert(  # type: ignore[attr-defined]
            content=content,
            index_names=index_name,
            vector=vector,
            metadata=extended_metadata,
        )

    def retrieve_triples(
        self,
        query_vector: np.ndarray,
        index_name: str = "triple_index",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve similar triples based on query vector.

        Args:
            query_vector: Embedding vector for the query
            index_name: Name of the index to search
            top_k: Number of results to return

        Returns:
            List of triples with scores:
            [{"query": ..., "passage": ..., "answer": ..., "score": ...}, ...]
        """

        # Filter for triple type
        def triple_filter(m: dict[str, Any]) -> bool:
            return m.get("type") == "triple"

        results = self.retrieve(  # type: ignore[attr-defined]
            query=query_vector,
            index_name=index_name,
            top_k=top_k,
            with_metadata=True,
            metadata_filter=triple_filter,
        )

        parsed: list[dict[str, Any]] = []
        for r in results:
            try:
                text = r.get("text", "")
                if not text:
                    continue
                triple = Triple.from_json(text)
                parsed.append(
                    {
                        "id": r.get("id"),
                        "query": triple.query,
                        "passage": triple.passage,
                        "answer": triple.answer,
                        "score": r.get("score", 0.0),
                        "metadata": r.get("metadata", {}),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        return parsed


# =============================================================================
# 5.2 Link Evolution (A-Mem)
# =============================================================================


class LinkEvolutionMixin:
    """
    Mixin for GraphMemoryCollection to support link evolution (A-Mem paper).

    Dynamically updates edge weights based on similarity and time decay.
    """

    def evolve_links(
        self,
        node_id: str,
        index_name: str = "default",
        similarity_threshold: float = 0.7,
        decay_factor: float = 0.95,
        reinforcement_factor: float = 0.2,
        max_weight: float = 2.0,
        min_weight: float = 0.1,
        get_vector_func: Callable[[str], np.ndarray | None] | None = None,
        find_similar_func: Callable[[np.ndarray, int], list[tuple[str, float]]] | None = None,
    ) -> int:
        """
        Evolve links for a node based on similarity.

        1. Decay existing edge weights
        2. Add/strengthen edges to similar nodes

        Args:
            node_id: The node to evolve links for
            index_name: Graph index name
            similarity_threshold: Minimum similarity to create edge
            decay_factor: Decay multiplier for existing edges (0-1)
            reinforcement_factor: Weight increase for similar nodes
            max_weight: Maximum edge weight
            min_weight: Edges below this weight are removed
            get_vector_func: Function to get node vector (node_id -> vector)
            find_similar_func: Function to find similar nodes (vector, k -> [(node_id, sim)])

        Returns:
            Number of edges updated
        """
        if not hasattr(self, "indexes"):
            return 0

        if index_name not in self.indexes:  # type: ignore[attr-defined]
            return 0

        graph_index = self.indexes[index_name]  # type: ignore[attr-defined]
        updated_count = 0

        # 1. Get node vector (if similarity functions provided)
        node_vector = None
        similar_nodes: list[tuple[str, float]] = []

        if get_vector_func is not None:
            node_vector = get_vector_func(node_id)

        if node_vector is not None and find_similar_func is not None:
            similar_nodes = find_similar_func(node_vector, 20)

        # 2. Decay existing edges
        current_neighbors = graph_index.get_neighbors(node_id, hop=1)
        for neighbor_id in current_neighbors:
            weight = graph_index.get_edge_weight(node_id, neighbor_id)
            if weight is None:
                continue
            new_weight = weight * decay_factor
            if new_weight < min_weight:
                graph_index.graph.remove_edge(node_id, neighbor_id)
            else:
                graph_index.graph.add_edge(node_id, neighbor_id, weight=new_weight)
            updated_count += 1

        # 3. Add/strengthen edges to similar nodes
        for neighbor_id, similarity in similar_nodes:
            if neighbor_id == node_id:
                continue
            if similarity < similarity_threshold:
                continue

            if graph_index.graph.has_edge(node_id, neighbor_id):
                # Strengthen existing edge
                current_weight = graph_index.get_edge_weight(node_id, neighbor_id) or 0.0
                new_weight = min(current_weight + similarity * reinforcement_factor, max_weight)
                graph_index.graph.add_edge(node_id, neighbor_id, weight=new_weight)
            else:
                # Add new edge
                graph_index.graph.add_edge(node_id, neighbor_id, weight=similarity)

            updated_count += 1

        return updated_count

    def batch_evolve_links(
        self,
        index_name: str = "default",
        decay_factor: float = 0.95,
        similarity_threshold: float = 0.7,
        get_vector_func: Callable[[str], np.ndarray | None] | None = None,
        find_similar_func: Callable[[np.ndarray, int], list[tuple[str, float]]] | None = None,
    ) -> int:
        """
        Batch evolve links for all nodes.

        Args:
            index_name: Graph index name
            decay_factor: Decay multiplier for existing edges
            similarity_threshold: Minimum similarity to create edge
            get_vector_func: Function to get node vector
            find_similar_func: Function to find similar nodes

        Returns:
            Total number of edges updated
        """
        total_updated = 0

        if not hasattr(self, "text_storage"):
            return 0

        for node_id in self.text_storage.get_all_ids():  # type: ignore[attr-defined]
            total_updated += self.evolve_links(
                node_id=node_id,
                index_name=index_name,
                decay_factor=decay_factor,
                similarity_threshold=similarity_threshold,
                get_vector_func=get_vector_func,
                find_similar_func=find_similar_func,
            )

        return total_updated


# =============================================================================
# 5.3 Ebbinghaus Forgetting Curve (MemoryBank)
# =============================================================================


@dataclass
class ForgettingConfig:
    """Configuration for Ebbinghaus forgetting."""

    strength_threshold: float = 0.3
    base_decay_rate: float = 0.1  # λ in exponential decay
    initial_strength: float = 0.8
    reinforcement_factor: float = 0.2
    max_strength: float = 1.0


class EbbinghausForgetting:
    """
    Ebbinghaus forgetting curve calculator.

    Memory strength decays exponentially over time but is reinforced by access.
    Formula: S = S0 * e^(-λt) + reinforcement * log(access_count + 1)
    """

    def __init__(self, config: ForgettingConfig | None = None):
        """
        Initialize forgetting calculator.

        Args:
            config: Forgetting configuration
        """
        self.config = config or ForgettingConfig()

    def calculate_strength(
        self,
        last_access_time: float,
        access_count: int,
        creation_time: float | None = None,
        current_time: float | None = None,
    ) -> float:
        """
        Calculate current memory strength.

        Args:
            last_access_time: Unix timestamp of last access
            access_count: Number of times accessed
            creation_time: Unix timestamp of creation (optional)
            current_time: Current time (default: now)

        Returns:
            Memory strength between 0 and 1
        """
        current_time = current_time or time.time()

        # Time since last access in hours
        elapsed_hours = max(0, (current_time - last_access_time) / 3600)

        # Base decay: S0 * e^(-λt)
        base_strength = self.config.initial_strength * math.exp(
            -self.config.base_decay_rate * elapsed_hours
        )

        # Reinforcement from access count: log(n+1) scaling
        reinforcement = self.config.reinforcement_factor * math.log(access_count + 1)

        # Combined strength, capped at max
        return min(base_strength + reinforcement, self.config.max_strength)

    def should_forget(self, metadata: dict[str, Any], current_time: float | None = None) -> bool:
        """
        Determine if a memory should be forgotten.

        Args:
            metadata: Metadata dict with 'last_access_time' and 'access_count'
            current_time: Current time (default: now)

        Returns:
            True if memory should be forgotten
        """
        last_access = metadata.get("last_access_time", 0)
        access_count = metadata.get("access_count", 0)

        # If never accessed, use creation time
        if last_access == 0:
            last_access = metadata.get("creation_time", time.time())

        strength = self.calculate_strength(
            last_access_time=last_access,
            access_count=access_count,
            current_time=current_time,
        )

        return strength < self.config.strength_threshold

    def get_strength_from_metadata(
        self, metadata: dict[str, Any], current_time: float | None = None
    ) -> float:
        """
        Get strength from metadata dict.

        Args:
            metadata: Metadata dict with access info
            current_time: Current time

        Returns:
            Memory strength
        """
        last_access = metadata.get("last_access_time", 0)
        access_count = metadata.get("access_count", 0)

        if last_access == 0:
            last_access = metadata.get("creation_time", time.time())

        return self.calculate_strength(
            last_access_time=last_access,
            access_count=access_count,
            current_time=current_time,
        )


class ForgettingMixin:
    """
    Mixin for Collections to support Ebbinghaus forgetting (MemoryBank paper).

    Provides methods to track access and apply forgetting.
    """

    def update_access(self, item_id: str) -> bool:
        """
        Update access time and count for an item.

        Args:
            item_id: Item ID to update

        Returns:
            True if updated successfully
        """
        if not hasattr(self, "metadata_storage"):
            return False

        metadata = self.metadata_storage.get(item_id)  # type: ignore[attr-defined]
        if metadata is None:
            return False

        # Ensure fields are registered
        for field_name in ["last_access_time", "access_count"]:
            if not self.metadata_storage.has_field(field_name):  # type: ignore[attr-defined]
                self.metadata_storage.add_field(field_name)  # type: ignore[attr-defined]

        # Update access info
        metadata["last_access_time"] = time.time()
        metadata["access_count"] = metadata.get("access_count", 0) + 1

        self.metadata_storage.store(item_id, metadata)  # type: ignore[attr-defined]
        return True

    def apply_forgetting(
        self,
        forgetting: EbbinghausForgetting | None = None,
        current_time: float | None = None,
    ) -> list[str]:
        """
        Apply forgetting curve and delete low-strength memories.

        Args:
            forgetting: Forgetting calculator (uses default if None)
            current_time: Current time for calculation

        Returns:
            List of forgotten (deleted) item IDs
        """
        if not hasattr(self, "metadata_storage") or not hasattr(self, "delete"):
            return []

        forgetting = forgetting or EbbinghausForgetting()
        forgotten_ids: list[str] = []

        # Get all IDs
        all_ids = self.get_all_ids()  # type: ignore[attr-defined]

        for item_id in all_ids:
            metadata = self.metadata_storage.get(item_id)  # type: ignore[attr-defined]
            if (
                metadata
                and forgetting.should_forget(metadata, current_time)
                and self.delete(item_id)  # type: ignore[attr-defined]
            ):
                forgotten_ids.append(item_id)

        return forgotten_ids

    def get_memory_strength(
        self,
        item_id: str,
        forgetting: EbbinghausForgetting | None = None,
        current_time: float | None = None,
    ) -> float:
        """
        Get the current strength of a memory.

        Args:
            item_id: Item ID
            forgetting: Forgetting calculator
            current_time: Current time

        Returns:
            Memory strength (0.0 if not found)
        """
        if not hasattr(self, "metadata_storage"):
            return 0.0

        metadata = self.metadata_storage.get(item_id)  # type: ignore[attr-defined]
        if not metadata:
            return 0.0

        forgetting = forgetting or EbbinghausForgetting()
        return forgetting.get_strength_from_metadata(metadata, current_time)


# =============================================================================
# 5.3.1 User Portrait (MemoryBank)
# =============================================================================


@dataclass
class UserPortrait:
    """
    User Portrait structure (MemoryBank paper).

    Stores user personality insights and event summaries at different granularities.
    """

    user_id: str = "default_user"
    daily_personality: dict[str, Any] = field(default_factory=dict)  # Per-day insights
    global_portrait: dict[str, Any] = field(default_factory=dict)  # Overall user profile
    daily_event_summary: str = ""  # Summary of today's events
    global_event_summary: str = ""  # Summary of all events
    last_updated: float = field(default_factory=time.time)
    daily_summaries: dict[str, str] = field(default_factory=dict)  # date -> summary

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "daily_personality": self.daily_personality,
            "global_portrait": self.global_portrait,
            "daily_event_summary": self.daily_event_summary,
            "global_event_summary": self.global_event_summary,
            "last_updated": self.last_updated,
            "daily_summaries": self.daily_summaries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserPortrait:
        """Create from dictionary."""
        return cls(
            user_id=data.get("user_id", "default_user"),
            daily_personality=data.get("daily_personality", {}),
            global_portrait=data.get("global_portrait", {}),
            daily_event_summary=data.get("daily_event_summary", ""),
            global_event_summary=data.get("global_event_summary", ""),
            last_updated=data.get("last_updated", time.time()),
            daily_summaries=data.get("daily_summaries", {}),
        )

    def update_daily_personality(self, date_key: str, insights: dict[str, Any]) -> None:
        """Update personality insights for a specific date."""
        self.daily_personality[date_key] = insights
        self.last_updated = time.time()

    def merge_to_global(self, new_insights: dict[str, Any]) -> None:
        """Merge daily insights into global portrait."""
        for key, value in new_insights.items():
            if key not in self.global_portrait:
                self.global_portrait[key] = value
            elif isinstance(value, list) and isinstance(self.global_portrait[key], list):
                # Merge lists and deduplicate
                self.global_portrait[key] = list(set(self.global_portrait[key] + value))
            elif isinstance(value, dict) and isinstance(self.global_portrait[key], dict):
                # Recursive merge for dicts
                self.global_portrait[key].update(value)
            else:
                # Override with new value
                self.global_portrait[key] = value
        self.last_updated = time.time()


class UserPortraitMixin:
    """
    Mixin for HierarchicalMemoryService to support User Portrait (MemoryBank paper).

    Provides methods for:
    - Storing and retrieving user portraits
    - Updating daily/global summaries after insert
    - Enhancing retrieval prompts with portrait information
    """

    _user_portraits: dict[str, UserPortrait]

    def _ensure_portraits_dict(self) -> None:
        """Ensure _user_portraits is initialized."""
        if not hasattr(self, "_user_portraits"):
            self._user_portraits = {}

    def get_user_portrait(self, user_id: str = "default_user") -> UserPortrait:
        """
        Get user portrait for a user.

        Args:
            user_id: User identifier

        Returns:
            UserPortrait instance
        """
        self._ensure_portraits_dict()
        if user_id not in self._user_portraits:
            self._user_portraits[user_id] = UserPortrait(user_id=user_id)
        return self._user_portraits[user_id]

    def update_user_portrait(
        self,
        user_id: str = "default_user",
        daily_personality: dict[str, Any] | None = None,
        global_portrait: dict[str, Any] | None = None,
        daily_event_summary: str | None = None,
        global_event_summary: str | None = None,
    ) -> UserPortrait:
        """
        Update user portrait.

        Args:
            user_id: User identifier
            daily_personality: Daily personality insights (date_key -> insights)
            global_portrait: Global portrait updates
            daily_event_summary: Today's event summary
            global_event_summary: Global event summary

        Returns:
            Updated UserPortrait
        """
        self._ensure_portraits_dict()
        portrait = self.get_user_portrait(user_id)

        if daily_personality:
            for date_key, insights in daily_personality.items():
                portrait.update_daily_personality(date_key, insights)

        if global_portrait:
            portrait.merge_to_global(global_portrait)

        if daily_event_summary is not None:
            portrait.daily_event_summary = daily_event_summary
            # Also store in daily_summaries with today's date
            from datetime import timezone

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            portrait.daily_summaries[today] = daily_event_summary

        if global_event_summary is not None:
            portrait.global_event_summary = global_event_summary

        portrait.last_updated = time.time()
        return portrait

    def get_portrait_context(self, user_id: str = "default_user") -> str:
        """
        Get portrait as context string for prompt enhancement.

        Args:
            user_id: User identifier

        Returns:
            Formatted context string
        """
        portrait = self.get_user_portrait(user_id)

        parts = []

        if portrait.global_portrait:
            parts.append("User Profile:")
            for key, value in portrait.global_portrait.items():
                if isinstance(value, list):
                    parts.append(f"  - {key}: {', '.join(str(v) for v in value)}")
                else:
                    parts.append(f"  - {key}: {value}")

        if portrait.global_event_summary:
            parts.append(f"\nEvent History: {portrait.global_event_summary}")

        if portrait.daily_event_summary:
            parts.append(f"\nRecent Events: {portrait.daily_event_summary}")

        return "\n".join(parts) if parts else ""

    def save_portraits(self) -> dict[str, dict[str, Any]]:
        """
        Get all portraits as serializable dict for persistence.

        Returns:
            Dict of user_id -> portrait_dict
        """
        self._ensure_portraits_dict()
        return {uid: p.to_dict() for uid, p in self._user_portraits.items()}

    def load_portraits(self, data: dict[str, dict[str, Any]]) -> None:
        """
        Load portraits from serialized data.

        Args:
            data: Dict of user_id -> portrait_dict
        """
        self._ensure_portraits_dict()
        for user_id, portrait_data in data.items():
            self._user_portraits[user_id] = UserPortrait.from_dict(portrait_data)


# =============================================================================
# 5.4 Heat Score Migration (MemoryOS)
# =============================================================================


@dataclass
class HeatConfig:
    """Configuration for heat score calculation."""

    cold_threshold: float = 0.3
    hot_threshold: float = 0.8
    decay_rate: float = 0.05  # Hourly decay rate for recency
    frequency_weight: float = 0.5
    recency_weight: float = 0.5
    max_frequency_contribution: float = 0.5


class HeatScoreManager:
    """
    Heat score manager for tier migration (MemoryOS paper).

    Calculates heat based on access frequency and recency.
    Hot memories are promoted, cold memories are demoted.
    """

    def __init__(self, config: HeatConfig | None = None):
        """
        Initialize heat score manager.

        Args:
            config: Heat configuration
        """
        self.config = config or HeatConfig()

    def calculate_heat(
        self,
        access_count: int,
        last_access_time: float,
        creation_time: float,
        current_time: float | None = None,
    ) -> float:
        """
        Calculate heat score for a memory.

        Considers:
        - Access frequency (normalized by age)
        - Recency of last access (exponential decay)

        Args:
            access_count: Number of accesses
            last_access_time: Unix timestamp of last access
            creation_time: Unix timestamp of creation
            current_time: Current time (default: now)

        Returns:
            Heat score between 0 and 1
        """
        current_time = current_time or time.time()

        # Access frequency contribution
        age_hours = max(1, (current_time - creation_time) / 3600)  # Avoid division by zero
        frequency = access_count / age_hours
        # Normalize with sigmoid-like function
        freq_score = min(
            frequency / (frequency + 1) * self.config.frequency_weight * 2,
            self.config.max_frequency_contribution,
        )

        # Recency contribution
        hours_since_access = max(0, (current_time - last_access_time) / 3600)
        recency_score = self.config.recency_weight * math.exp(
            -self.config.decay_rate * hours_since_access
        )

        return min(freq_score + recency_score, 1.0)

    def get_heat_from_metadata(
        self, metadata: dict[str, Any], current_time: float | None = None
    ) -> float:
        """
        Calculate heat from metadata dict.

        Args:
            metadata: Metadata with access_count, last_access_time, creation_time
            current_time: Current time

        Returns:
            Heat score
        """
        access_count = metadata.get("access_count", 0)
        last_access_time = metadata.get("last_access_time", 0)
        creation_time = metadata.get("creation_time", time.time())

        # Use creation time if never accessed
        if last_access_time == 0:
            last_access_time = creation_time

        return self.calculate_heat(
            access_count=access_count,
            last_access_time=last_access_time,
            creation_time=creation_time,
            current_time=current_time,
        )

    def get_migration_action(self, heat: float) -> str | None:
        """
        Determine migration action based on heat.

        Args:
            heat: Heat score

        Returns:
            "promote" for hot, "demote" for cold, None for stable
        """
        if heat < self.config.cold_threshold:
            return "demote"
        if heat > self.config.hot_threshold:
            return "promote"
        return None


class HeatMigrationMixin:
    """
    Mixin for hierarchical services to support heat-based migration.

    Works with services that have tier_collections.
    """

    def get_all_heat_scores(
        self,
        heat_manager: HeatScoreManager | None = None,
        current_time: float | None = None,
    ) -> dict[str, float]:
        """
        Get heat scores for all items.

        Args:
            heat_manager: Heat score manager
            current_time: Current time

        Returns:
            Dict of item_id -> heat_score
        """
        if not hasattr(self, "metadata_storage") or not hasattr(self, "get_all_ids"):
            return {}

        heat_manager = heat_manager or HeatScoreManager()
        heat_scores: dict[str, float] = {}

        for item_id in self.get_all_ids():  # type: ignore[attr-defined]
            metadata = self.metadata_storage.get(item_id)  # type: ignore[attr-defined]
            if metadata:
                heat_scores[item_id] = heat_manager.get_heat_from_metadata(metadata, current_time)

        return heat_scores


# =============================================================================
# 5.4.1 MemGPT Three-Tier Storage
# =============================================================================


@dataclass
class MemGPTWorkingContext:
    """
    MemGPT Working Context storage.

    Structured KV storage for current facts and conversation state.
    """

    facts: dict[str, str] = field(default_factory=dict)  # key -> fact
    system_state: dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)

    def set_fact(self, key: str, value: str) -> None:
        """Set a fact in working context."""
        self.facts[key] = value
        self.last_updated = time.time()

    def get_fact(self, key: str) -> str | None:
        """Get a fact from working context."""
        return self.facts.get(key)

    def remove_fact(self, key: str) -> bool:
        """Remove a fact from working context."""
        if key in self.facts:
            del self.facts[key]
            self.last_updated = time.time()
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "facts": self.facts,
            "system_state": self.system_state,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemGPTWorkingContext:
        """Create from dictionary."""
        return cls(
            facts=data.get("facts", {}),
            system_state=data.get("system_state", {}),
            last_updated=data.get("last_updated", time.time()),
        )


@dataclass
class MemGPTMessage:
    """A message in MemGPT FIFO queue."""

    message_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemGPTMessage:
        """Create from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid4())),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class MemGPTStorageMixin:
    """
    Mixin for HierarchicalMemoryService to support MemGPT three-tier storage.

    Provides:
    - Working Context: Structured KV for current facts
    - FIFO Queue: Short-term message queue with persistence on eviction
    - Recall Storage: All evicted messages (searchable)
    """

    _working_context: MemGPTWorkingContext
    _fifo_queue: deque[MemGPTMessage]
    _fifo_capacity: int
    _recall_storage: list[MemGPTMessage]

    def _ensure_memgpt_storage(self) -> None:
        """Ensure MemGPT storage is initialized."""
        if not hasattr(self, "_working_context"):
            self._working_context = MemGPTWorkingContext()
        if not hasattr(self, "_fifo_queue"):
            self._fifo_queue = deque()
        if not hasattr(self, "_fifo_capacity"):
            self._fifo_capacity = 100
        if not hasattr(self, "_recall_storage"):
            self._recall_storage = []

    def set_fifo_capacity(self, capacity: int) -> None:
        """Set FIFO queue capacity."""
        self._ensure_memgpt_storage()
        self._fifo_capacity = capacity

    # --- Working Context Methods ---

    def get_working_context(self) -> MemGPTWorkingContext:
        """Get current working context."""
        self._ensure_memgpt_storage()
        return self._working_context

    def set_working_fact(self, key: str, value: str) -> None:
        """Set a fact in working context."""
        self._ensure_memgpt_storage()
        self._working_context.set_fact(key, value)

    def get_working_fact(self, key: str) -> str | None:
        """Get a fact from working context."""
        self._ensure_memgpt_storage()
        return self._working_context.get_fact(key)

    def replace_working_fact(self, old_key: str, new_key: str, new_value: str) -> bool:
        """
        Replace a fact in working context (MemGPT core operation).

        Args:
            old_key: Key to remove
            new_key: New key to add
            new_value: New value

        Returns:
            True if old key existed and was replaced
        """
        self._ensure_memgpt_storage()
        existed = self._working_context.remove_fact(old_key)
        self._working_context.set_fact(new_key, new_value)
        return existed

    # --- FIFO Queue Methods ---

    def push_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Push a message to FIFO queue.

        If queue is full, evicts oldest message to recall storage.

        Args:
            role: Message role
            content: Message content
            metadata: Optional metadata

        Returns:
            Message ID
        """
        self._ensure_memgpt_storage()

        message = MemGPTMessage(
            message_id=str(uuid4()),
            role=role,
            content=content,
            metadata=metadata or {},
        )

        # Evict to recall if at capacity
        if len(self._fifo_queue) >= self._fifo_capacity:
            evicted = self._fifo_queue.popleft()
            self._recall_storage.append(evicted)

        self._fifo_queue.append(message)
        return message.message_id

    def get_recent_messages(self, n: int | None = None) -> list[MemGPTMessage]:
        """
        Get recent messages from FIFO queue.

        Args:
            n: Number of messages (None = all)

        Returns:
            List of messages (oldest first)
        """
        self._ensure_memgpt_storage()
        if n is None:
            return list(self._fifo_queue)
        return list(self._fifo_queue)[-n:] if n > 0 else []

    def get_fifo_count(self) -> int:
        """Get number of messages in FIFO queue."""
        self._ensure_memgpt_storage()
        return len(self._fifo_queue)

    # --- Recall Storage Methods ---

    def search_recall(
        self,
        query: str,
        top_k: int = 10,
        search_func: Callable[[str, list[MemGPTMessage], int], list[MemGPTMessage]] | None = None,
    ) -> list[MemGPTMessage]:
        """
        Search recall storage for evicted messages.

        Args:
            query: Search query
            top_k: Number of results
            search_func: Custom search function (default: simple text match)

        Returns:
            List of matching messages
        """
        self._ensure_memgpt_storage()

        if search_func:
            return search_func(query, self._recall_storage, top_k)

        # Simple text match fallback
        query_lower = query.lower()
        matches = [msg for msg in self._recall_storage if query_lower in msg.content.lower()]
        return matches[:top_k]

    def get_recall_count(self) -> int:
        """Get number of messages in recall storage."""
        self._ensure_memgpt_storage()
        return len(self._recall_storage)

    def get_all_recall(self) -> list[MemGPTMessage]:
        """Get all messages from recall storage."""
        self._ensure_memgpt_storage()
        return list(self._recall_storage)

    # --- Persistence ---

    def save_memgpt_state(self) -> dict[str, Any]:
        """Save MemGPT state for persistence."""
        self._ensure_memgpt_storage()
        return {
            "working_context": self._working_context.to_dict(),
            "fifo_queue": [msg.to_dict() for msg in self._fifo_queue],
            "fifo_capacity": self._fifo_capacity,
            "recall_storage": [msg.to_dict() for msg in self._recall_storage],
        }

    def load_memgpt_state(self, data: dict[str, Any]) -> None:
        """Load MemGPT state from persistence."""
        self._ensure_memgpt_storage()
        if "working_context" in data:
            self._working_context = MemGPTWorkingContext.from_dict(data["working_context"])
        if "fifo_queue" in data:
            self._fifo_queue = deque(MemGPTMessage.from_dict(msg) for msg in data["fifo_queue"])
        if "fifo_capacity" in data:
            self._fifo_capacity = data["fifo_capacity"]
        if "recall_storage" in data:
            self._recall_storage = [MemGPTMessage.from_dict(msg) for msg in data["recall_storage"]]


# =============================================================================
# 5.4.2 MemoryOS Segment-Page Architecture
# =============================================================================


@dataclass
class MemoryOSPage:
    """A dialogue page in MemoryOS MTM layer."""

    page_id: str
    content: str
    timestamp: float = field(default_factory=time.time)
    segment_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page_id": self.page_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "segment_id": self.segment_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryOSPage:
        """Create from dictionary."""
        return cls(
            page_id=data.get("page_id", str(uuid4())),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", time.time()),
            segment_id=data.get("segment_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MemoryOSSegment:
    """
    A segment in MemoryOS MTM layer.

    Groups related dialogue pages by topic with semantic summary.
    """

    segment_id: str
    pages: list[str] = field(default_factory=list)  # List of page_ids
    summary: str = ""
    heat: float = 0.5
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    topic_embedding: np.ndarray | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "segment_id": self.segment_id,
            "pages": self.pages,
            "summary": self.summary,
            "heat": self.heat,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            # topic_embedding stored separately
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], embedding: np.ndarray | None = None
    ) -> MemoryOSSegment:
        """Create from dictionary."""
        return cls(
            segment_id=data.get("segment_id", str(uuid4())),
            pages=data.get("pages", []),
            summary=data.get("summary", ""),
            heat=data.get("heat", 0.5),
            created_at=data.get("created_at", time.time()),
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 0),
            topic_embedding=embedding,
        )

    def add_page(self, page_id: str) -> None:
        """Add a page to this segment."""
        if page_id not in self.pages:
            self.pages.append(page_id)

    def update_heat(self, decay_rate: float = 0.05) -> None:
        """Update heat score based on recency and access."""
        hours_since_access = (time.time() - self.last_accessed) / 3600
        recency_factor = math.exp(-decay_rate * hours_since_access)
        frequency_factor = min(0.5, self.access_count / (self.access_count + 10))
        self.heat = 0.5 * recency_factor + 0.5 * frequency_factor

    def record_access(self) -> None:
        """Record an access to this segment."""
        self.last_accessed = time.time()
        self.access_count += 1
        self.update_heat()


class SegmentPageMixin:
    """
    Mixin for HierarchicalMemoryService to support MemoryOS Segment-Page architecture.

    Provides:
    - Page management in MTM layer
    - Segment clustering based on Fscore
    - Heat-based segment management
    """

    _segments: dict[str, MemoryOSSegment]
    _pages: dict[str, MemoryOSPage]
    _segment_similarity_threshold: float

    def _ensure_segment_storage(self) -> None:
        """Ensure segment storage is initialized."""
        if not hasattr(self, "_segments"):
            self._segments = {}
        if not hasattr(self, "_pages"):
            self._pages = {}
        if not hasattr(self, "_segment_similarity_threshold"):
            self._segment_similarity_threshold = 0.7

    def set_segment_threshold(self, threshold: float) -> None:
        """Set similarity threshold for segment assignment."""
        self._ensure_segment_storage()
        self._segment_similarity_threshold = threshold

    # --- Page Methods ---

    def add_page(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        page_id: str | None = None,
    ) -> str:
        """
        Add a dialogue page.

        Args:
            content: Page content
            metadata: Optional metadata
            page_id: Optional page ID

        Returns:
            Page ID
        """
        self._ensure_segment_storage()
        page = MemoryOSPage(
            page_id=page_id or str(uuid4()),
            content=content,
            metadata=metadata or {},
        )
        self._pages[page.page_id] = page
        return page.page_id

    def get_page(self, page_id: str) -> MemoryOSPage | None:
        """Get a page by ID."""
        self._ensure_segment_storage()
        return self._pages.get(page_id)

    # --- Segment Methods ---

    def create_segment(
        self,
        summary: str = "",
        initial_heat: float = 0.5,
        segment_id: str | None = None,
        topic_embedding: np.ndarray | None = None,
    ) -> str:
        """
        Create a new segment.

        Args:
            summary: Segment summary
            initial_heat: Initial heat score
            segment_id: Optional segment ID
            topic_embedding: Optional topic embedding

        Returns:
            Segment ID
        """
        self._ensure_segment_storage()
        segment = MemoryOSSegment(
            segment_id=segment_id or str(uuid4()),
            summary=summary,
            heat=initial_heat,
            topic_embedding=topic_embedding,
        )
        self._segments[segment.segment_id] = segment
        return segment.segment_id

    def get_segment(self, segment_id: str) -> MemoryOSSegment | None:
        """Get a segment by ID."""
        self._ensure_segment_storage()
        return self._segments.get(segment_id)

    def assign_page_to_segment(
        self,
        page_id: str,
        page_embedding: np.ndarray | None = None,
        get_segment_embedding: Callable[[str], np.ndarray | None] | None = None,
    ) -> str | None:
        """
        Assign a page to the best matching segment based on Fscore.

        If no segment matches above threshold, creates a new segment.

        Args:
            page_id: Page ID to assign
            page_embedding: Embedding of the page content
            get_segment_embedding: Function to get segment embedding by ID

        Returns:
            Assigned segment ID
        """
        self._ensure_segment_storage()

        page = self._pages.get(page_id)
        if not page:
            return None

        best_segment_id: str | None = None
        best_score = 0.0

        if page_embedding is not None and get_segment_embedding:
            # Find best matching segment
            for segment_id, _segment in self._segments.items():
                seg_embedding = get_segment_embedding(segment_id)
                if seg_embedding is not None:
                    # Cosine similarity as Fscore proxy
                    similarity = float(
                        np.dot(page_embedding, seg_embedding)
                        / (np.linalg.norm(page_embedding) * np.linalg.norm(seg_embedding) + 1e-8)
                    )
                    if similarity > best_score:
                        best_score = similarity
                        best_segment_id = segment_id

        # Create new segment if no match above threshold
        if best_segment_id is None or best_score < self._segment_similarity_threshold:
            best_segment_id = self.create_segment(
                summary=page.content[:100] + "...",  # Initial summary
                topic_embedding=page_embedding,
            )

        # Assign page to segment
        segment = self._segments[best_segment_id]
        segment.add_page(page_id)
        page.segment_id = best_segment_id

        return best_segment_id

    def get_hot_segments(self, threshold: float = 0.7) -> list[MemoryOSSegment]:
        """Get segments with heat above threshold."""
        self._ensure_segment_storage()
        return [s for s in self._segments.values() if s.heat >= threshold]

    def get_cold_segments(self, threshold: float = 0.3) -> list[MemoryOSSegment]:
        """Get segments with heat below threshold."""
        self._ensure_segment_storage()
        return [s for s in self._segments.values() if s.heat < threshold]

    def update_all_segment_heats(self) -> None:
        """Update heat scores for all segments."""
        self._ensure_segment_storage()
        for segment in self._segments.values():
            segment.update_heat()

    # --- Persistence ---

    def save_segment_state(self) -> dict[str, Any]:
        """Save segment state for persistence."""
        self._ensure_segment_storage()
        return {
            "segments": {sid: s.to_dict() for sid, s in self._segments.items()},
            "pages": {pid: p.to_dict() for pid, p in self._pages.items()},
            "threshold": self._segment_similarity_threshold,
        }

    def load_segment_state(self, data: dict[str, Any]) -> None:
        """Load segment state from persistence."""
        self._ensure_segment_storage()
        if "segments" in data:
            self._segments = {
                sid: MemoryOSSegment.from_dict(s) for sid, s in data["segments"].items()
            }
        if "pages" in data:
            self._pages = {pid: MemoryOSPage.from_dict(p) for pid, p in data["pages"].items()}
        if "threshold" in data:
            self._segment_similarity_threshold = data["threshold"]


# =============================================================================
# 5.4.3 MemoryOS Long-term Personal Memory (LPM)
# =============================================================================


@dataclass
class UserPersona:
    """User persona in MemoryOS LPM."""

    profile: dict[str, Any] = field(default_factory=dict)  # Static user profile
    kb: deque = field(default_factory=lambda: deque(maxlen=100))  # FIFO knowledge base
    traits: np.ndarray | None = None  # 90-dimensional dynamic trait vector (paper spec)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "profile": self.profile,
            "kb": list(self.kb),
            # traits stored separately as numpy array
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], traits: np.ndarray | None = None) -> UserPersona:
        """Create from dictionary."""
        kb_data = data.get("kb", [])
        kb: deque[Any] = deque(kb_data, maxlen=100)
        return cls(
            profile=data.get("profile", {}),
            kb=kb,
            traits=traits,
        )


@dataclass
class AgentPersona:
    """Agent persona in MemoryOS LPM."""

    profile: dict[str, Any] = field(default_factory=dict)  # Static agent profile
    traits: deque = field(default_factory=lambda: deque(maxlen=50))  # FIFO trait queue

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "profile": self.profile,
            "traits": list(self.traits),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentPersona:
        """Create from dictionary."""
        traits_data = data.get("traits", [])
        traits: deque[Any] = deque(traits_data, maxlen=50)
        return cls(
            profile=data.get("profile", {}),
            traits=traits,
        )


@dataclass
class MemoryOSLPM:
    """
    Long-term Personal Memory structure (MemoryOS paper).

    Contains both user and agent personas.
    """

    user_persona: UserPersona = field(default_factory=UserPersona)
    agent_persona: AgentPersona = field(default_factory=AgentPersona)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_persona": self.user_persona.to_dict(),
            "agent_persona": self.agent_persona.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], user_traits: np.ndarray | None = None) -> MemoryOSLPM:
        """Create from dictionary."""
        return cls(
            user_persona=UserPersona.from_dict(data.get("user_persona", {}), traits=user_traits),
            agent_persona=AgentPersona.from_dict(data.get("agent_persona", {})),
        )


class LPMMixin:
    """
    Mixin for HierarchicalMemoryService to support MemoryOS LPM.

    Provides:
    - User persona management (profile, knowledge base, trait vector)
    - Agent persona management (profile, traits queue)
    - Persona extraction from high-heat segments
    """

    _lpm: MemoryOSLPM

    def _ensure_lpm(self) -> None:
        """Ensure LPM is initialized."""
        if not hasattr(self, "_lpm"):
            self._lpm = MemoryOSLPM()

    def get_lpm(self) -> MemoryOSLPM:
        """Get LPM instance."""
        self._ensure_lpm()
        return self._lpm

    # --- User Persona Methods ---

    def update_user_profile(self, profile_updates: dict[str, Any]) -> None:
        """Update static user profile."""
        self._ensure_lpm()
        self._lpm.user_persona.profile.update(profile_updates)

    def add_user_knowledge(self, knowledge: str) -> None:
        """Add knowledge to user's FIFO knowledge base."""
        self._ensure_lpm()
        self._lpm.user_persona.kb.append(knowledge)

    def set_user_traits(self, traits: np.ndarray) -> None:
        """Set user's dynamic trait vector."""
        self._ensure_lpm()
        self._lpm.user_persona.traits = traits

    def get_user_traits(self) -> np.ndarray | None:
        """Get user's trait vector."""
        self._ensure_lpm()
        return self._lpm.user_persona.traits

    # --- Agent Persona Methods ---

    def update_agent_profile(self, profile_updates: dict[str, Any]) -> None:
        """Update static agent profile."""
        self._ensure_lpm()
        self._lpm.agent_persona.profile.update(profile_updates)

    def add_agent_trait(self, trait: str) -> None:
        """Add trait to agent's FIFO trait queue."""
        self._ensure_lpm()
        self._lpm.agent_persona.traits.append(trait)

    # --- Extraction from Segments ---

    def extract_persona_from_segments(
        self,
        hot_segments: list[Any],
        extract_func: Callable[[list[Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Extract persona information from high-heat segments.

        Args:
            hot_segments: List of hot segments to extract from
            extract_func: Custom extraction function

        Returns:
            Extracted persona information
        """
        self._ensure_lpm()

        if extract_func:
            return extract_func(hot_segments)

        # Default: simple concatenation of segment summaries
        summaries = [s.summary if hasattr(s, "summary") else str(s) for s in hot_segments]
        return {"extracted_from_segments": summaries}

    # --- Retrieval Context ---

    def get_persona_context(self) -> str:
        """Get persona information as context string for prompts."""
        self._ensure_lpm()

        parts = []

        # User profile
        if self._lpm.user_persona.profile:
            parts.append("User Profile:")
            for k, v in self._lpm.user_persona.profile.items():
                parts.append(f"  - {k}: {v}")

        # Recent user knowledge
        if self._lpm.user_persona.kb:
            parts.append("\nUser Knowledge:")
            for knowledge in list(self._lpm.user_persona.kb)[-5:]:
                parts.append(f"  - {knowledge}")

        # Agent profile
        if self._lpm.agent_persona.profile:
            parts.append("\nAgent Profile:")
            for k, v in self._lpm.agent_persona.profile.items():
                parts.append(f"  - {k}: {v}")

        return "\n".join(parts) if parts else ""

    # --- Persistence ---

    def save_lpm_state(self) -> dict[str, Any]:
        """Save LPM state for persistence."""
        self._ensure_lpm()
        state = self._lpm.to_dict()
        # Handle numpy traits separately
        if self._lpm.user_persona.traits is not None:
            state["user_traits_list"] = self._lpm.user_persona.traits.tolist()
        return state

    def load_lpm_state(self, data: dict[str, Any]) -> None:
        """Load LPM state from persistence."""
        user_traits = None
        if "user_traits_list" in data:
            user_traits = np.array(data["user_traits_list"])
        self._lpm = MemoryOSLPM.from_dict(data, user_traits=user_traits)


# =============================================================================
# 5.5 Token Budget Filtering (SCM)
# =============================================================================


class TokenCounter(Protocol):
    """Protocol for token counting."""

    def count(self, text: str) -> int:
        """Count tokens in text."""
        ...


class SimpleTokenCounter:
    """Simple token counter using character-based estimation."""

    def __init__(self, chars_per_token: float = 4.0):
        """
        Initialize counter.

        Args:
            chars_per_token: Average characters per token
        """
        self.chars_per_token = chars_per_token

    def count(self, text: str) -> int:
        """
        Estimate token count.

        Args:
            text: Text to count

        Returns:
            Estimated token count
        """
        return max(1, int(len(text) / self.chars_per_token))


class TiktokenCounter:
    """Token counter using tiktoken (OpenAI's tokenizer)."""

    def __init__(self, model: str = "gpt-4"):
        """
        Initialize with tiktoken.

        Args:
            model: Model name for encoding
        """
        try:
            import tiktoken

            self.encoding = tiktoken.encoding_for_model(model)
        except ImportError as err:
            raise ImportError(
                "tiktoken is required for TiktokenCounter. Install with: pip install tiktoken"
            ) from err

    def count(self, text: str) -> int:
        """
        Count tokens using tiktoken.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        return len(self.encoding.encode(text))


@dataclass
class TokenBudgetConfig:
    """Configuration for token budget filtering."""

    default_budget: int = 2000
    reserve_tokens: int = 100  # Reserve for system prompt etc
    chars_per_token: float = 4.0


class TokenBudgetFilter:
    """
    Token budget filter for context window management (SCM paper).

    Filters results to fit within a token budget.
    """

    def __init__(
        self,
        counter: TokenCounter | None = None,
        config: TokenBudgetConfig | None = None,
    ):
        """
        Initialize filter.

        Args:
            counter: Token counter (default: SimpleTokenCounter)
            config: Budget configuration
        """
        self.config = config or TokenBudgetConfig()
        self.counter = counter or SimpleTokenCounter(self.config.chars_per_token)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        return self.counter.count(text)

    def filter_by_budget(
        self,
        items: list[dict[str, Any]],
        budget: int | None = None,
        text_key: str = "text",
    ) -> list[dict[str, Any]]:
        """
        Filter items to fit within token budget.

        Assumes items are already sorted by importance/relevance.

        Args:
            items: List of result dicts with text
            budget: Token budget (default from config)
            text_key: Key for text field in items

        Returns:
            Filtered items within budget
        """
        budget = budget or self.config.default_budget
        effective_budget = budget - self.config.reserve_tokens

        result: list[dict[str, Any]] = []
        used_tokens = 0

        for item in items:
            text = item.get(text_key, "")
            if not text:
                continue

            tokens = self.count_tokens(text)

            if used_tokens + tokens > effective_budget:
                break

            result.append(item)
            used_tokens += tokens

        return result

    def get_budget_utilization(
        self,
        items: list[dict[str, Any]],
        budget: int | None = None,
        text_key: str = "text",
    ) -> dict[str, Any]:
        """
        Get budget utilization statistics.

        Args:
            items: Items to analyze
            budget: Token budget
            text_key: Key for text field

        Returns:
            Utilization stats
        """
        budget = budget or self.config.default_budget
        effective_budget = budget - self.config.reserve_tokens

        total_tokens = sum(self.count_tokens(item.get(text_key, "")) for item in items)

        return {
            "total_items": len(items),
            "total_tokens": total_tokens,
            "budget": budget,
            "effective_budget": effective_budget,
            "utilization": total_tokens / effective_budget if effective_budget > 0 else 0,
            "over_budget": total_tokens > effective_budget,
        }


class TokenBudgetMixin:
    """
    Mixin for Collections to support token budget filtering.
    """

    def retrieve_with_budget(
        self,
        query: np.ndarray,
        index_name: str,
        token_budget: int = 2000,
        max_candidates: int = 50,
        budget_filter: TokenBudgetFilter | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Retrieve items within token budget.

        Args:
            query: Query vector
            index_name: Index to search
            token_budget: Maximum tokens
            max_candidates: Candidates to fetch before filtering
            budget_filter: Token budget filter
            **kwargs: Additional retrieve arguments

        Returns:
            Results within token budget
        """
        if not hasattr(self, "retrieve"):
            return []

        # Fetch more candidates than needed
        candidates = self.retrieve(  # type: ignore[attr-defined]
            query=query,
            index_name=index_name,
            top_k=max_candidates,
            with_metadata=True,
            **kwargs,
        )

        # Apply budget filter
        budget_filter = budget_filter or TokenBudgetFilter()
        return budget_filter.filter_by_budget(candidates, token_budget)


# =============================================================================
# 5.6 Conflict Detection (Mem0)
# =============================================================================


@dataclass
class ConflictResult:
    """Result of conflict detection."""

    has_conflict: bool
    conflicting_item: dict[str, Any] | None = None
    conflict_type: str | None = None  # "entity_attribute", "semantic", "direct"
    similarity: float = 0.0


class EntityAttributeExtractor:
    """
    Extracts (entity, attribute) pairs from text.

    Supports patterns like:
    - "Entity's attribute is value"
    - "Entity has attribute value"
    - "The attribute of Entity is value"
    """

    # Patterns for entity-attribute extraction
    PATTERNS = [
        # "John's age is 25"
        r"^(.+?)'s\s+(.+?)\s+(?:is|are|was|were)\s+(.+)$",
        # "John has age 25"
        r"^(.+?)\s+(?:has|have|had)\s+(.+?)\s+(.+)$",
        # "The age of John is 25"
        r"^(?:The\s+)?(.+?)\s+of\s+(.+?)\s+(?:is|are|was|were)\s+(.+)$",
    ]

    def extract(self, text: str) -> tuple[str, str, str] | None:
        """
        Extract (entity, attribute, value) from text.

        Args:
            text: Text to extract from

        Returns:
            Tuple of (entity, attribute, value) or None
        """
        text = text.strip()

        for pattern in self.PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    return (groups[0].strip(), groups[1].strip(), groups[2].strip())

        return None

    def get_entity_attribute_key(self, text: str) -> tuple[str, str] | None:
        """
        Get (entity, attribute) key for conflict detection.

        Args:
            text: Text to extract from

        Returns:
            Tuple of (entity, attribute) or None
        """
        result = self.extract(text)
        if result:
            return (result[0], result[1])
        return None


@dataclass
class ConflictConfig:
    """Configuration for conflict detection."""

    semantic_threshold: float = 0.85
    enable_entity_attribute: bool = True
    enable_semantic: bool = True
    resolution_strategy: str = "skip"  # "skip", "replace", "append"


class ConflictDetector:
    """
    Conflict detector for facts (Mem0 paper).

    Detects conflicts between new facts and existing ones.
    """

    def __init__(self, config: ConflictConfig | None = None):
        """
        Initialize detector.

        Args:
            config: Detection configuration
        """
        self.config = config or ConflictConfig()
        self.extractor = EntityAttributeExtractor()

    def detect(
        self,
        new_fact: str,
        existing_facts: list[dict[str, Any]],
        new_vector: np.ndarray | None = None,
        get_vector_func: Callable[[str], np.ndarray | None] | None = None,
    ) -> ConflictResult:
        """
        Detect conflict between new fact and existing facts.

        Args:
            new_fact: New fact text
            existing_facts: List of existing fact dicts with 'text' key
            new_vector: Vector for new fact (for semantic comparison)
            get_vector_func: Function to get vector for text

        Returns:
            ConflictResult with conflict info
        """
        # 1. Entity-attribute conflict detection
        if self.config.enable_entity_attribute:
            new_ea = self.extractor.get_entity_attribute_key(new_fact)
            if new_ea:
                for fact in existing_facts:
                    existing_text = fact.get("text", "")
                    existing_ea = self.extractor.get_entity_attribute_key(existing_text)

                    if existing_ea and new_ea == existing_ea:
                        return ConflictResult(
                            has_conflict=True,
                            conflicting_item=fact,
                            conflict_type="entity_attribute",
                            similarity=1.0,
                        )

        # 2. Semantic conflict detection
        if self.config.enable_semantic and new_vector is not None:
            for fact in existing_facts:
                existing_vector = None
                if get_vector_func:
                    existing_vector = get_vector_func(fact.get("text", ""))

                if existing_vector is not None:
                    # Cosine similarity
                    similarity = float(
                        np.dot(new_vector, existing_vector)
                        / (np.linalg.norm(new_vector) * np.linalg.norm(existing_vector) + 1e-8)
                    )

                    if similarity > self.config.semantic_threshold:
                        return ConflictResult(
                            has_conflict=True,
                            conflicting_item=fact,
                            conflict_type="semantic",
                            similarity=similarity,
                        )

        return ConflictResult(has_conflict=False)


class ConflictDetectionMixin:
    """
    Mixin for Collections to support conflict detection.
    """

    def insert_with_conflict_check(
        self,
        text: str | None = None,
        content: str | None = None,
        vector: np.ndarray | None = None,
        index_name: str | None = None,
        detector: ConflictDetector | None = None,
        resolution: str = "skip",  # "skip", "replace", "append"
        metadata: dict[str, Any] | None = None,
        get_vector_func: Callable[[str], np.ndarray | None] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Insert with conflict detection.

        Args:
            text: Text content (UnifiedCollection interface)
            content: Text content (legacy interface)
            vector: Content vector (optional for UnifiedCollection)
            index_name: Index name
            detector: Conflict detector
            resolution: Conflict resolution strategy
            metadata: Additional metadata
            get_vector_func: Function to get vector for text
            **kwargs: Additional insert arguments

        Returns:
            Result dict with:
            - "id": inserted ID or None
            - "action": "inserted", "skipped", or "replaced"
            - "conflict": conflicting item or None
        """
        # Support both text= (UnifiedCollection) and content= (legacy)
        text_content = text or content
        if not text_content or not index_name:
            return {"id": None, "action": "error", "conflict": None}
        if (
            not hasattr(self, "retrieve")
            or not hasattr(self, "insert")
            or not hasattr(self, "delete")
        ):
            return {"id": None, "action": "error", "conflict": None}

        detector = detector or ConflictDetector()

        # For UnifiedCollection, use text query; for legacy, use vector
        query_param = text_content if hasattr(self, "_is_unified_collection") else vector

        # Retrieve similar items for conflict check
        similar_items = self.retrieve(  # type: ignore[attr-defined]
            query=query_param,
            index_name=index_name,
            top_k=10,
            with_metadata=True,
        )

        # Detect conflicts
        conflict_result = detector.detect(
            new_fact=text_content,
            existing_facts=similar_items,
            new_vector=vector,
            get_vector_func=get_vector_func,
        )

        if conflict_result.has_conflict:
            conflict_item = conflict_result.conflicting_item

            if resolution == "skip":
                return {
                    "id": None,
                    "action": "skipped",
                    "conflict": conflict_item,
                }

            if resolution == "replace":
                # Delete old, insert new
                if conflict_item and "id" in conflict_item:
                    self.delete(conflict_item["id"])  # type: ignore[attr-defined]

                # Support both UnifiedCollection and legacy Collection
                if hasattr(self, "_is_unified_collection"):
                    new_id = self.insert(  # type: ignore[attr-defined]
                        text=text_content,
                        metadata=metadata or {},
                        index_names=[index_name] if isinstance(index_name, str) else index_name,
                    )
                else:
                    new_id = self.insert(  # type: ignore[attr-defined]
                        content=text_content,
                        index_names=index_name,
                        vector=vector,
                        metadata=metadata,
                        **kwargs,
                    )
                return {
                    "id": new_id,
                    "action": "replaced",
                    "conflict": conflict_item,
                }

        # No conflict, normal insert
        # Support both UnifiedCollection and legacy Collection
        if hasattr(self, "_is_unified_collection"):
            new_id = self.insert(  # type: ignore[attr-defined]
                text=text_content,
                metadata=metadata or {},
                index_names=[index_name] if isinstance(index_name, str) else index_name,
            )
        else:
            new_id = self.insert(  # type: ignore[attr-defined]
                content=text_content,
                index_names=index_name,
                vector=vector,
                metadata=metadata,
                **kwargs,
            )
        return {
            "id": new_id,
            "action": "inserted",
            "conflict": None,
        }


# =============================================================================
# 5.7 HippoRAG Node Type Distinction
# =============================================================================


class NodeType:
    """Node types for HippoRAG knowledge graph."""

    PHRASE = "phrase"  # Entity/concept nodes (e.g., "Erik Hort")
    PASSAGE = "passage"  # Original passage nodes
    QUERY = "query"  # Query nodes (for HippoRAG2)


class EdgeType:
    """Edge types for HippoRAG knowledge graph."""

    RELATION = "relation"  # Semantic relationship between phrases
    SYNONYM = "synonym"  # Synonym link between similar phrases
    CONTAINS = "contains"  # Passage contains phrase
    TEMPORAL = "temporal"  # Temporal relationship


@dataclass
class HippoRAGNode:
    """
    A node in HippoRAG knowledge graph.

    Distinguishes between phrase nodes (entities) and passage nodes (documents).
    """

    node_id: str
    content: str
    node_type: str = NodeType.PHRASE  # "phrase" or "passage"
    embedding: np.ndarray | None = None
    source_passage_id: str | None = None  # For phrase nodes, the source passage
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "node_type": self.node_type,
            "source_passage_id": self.source_passage_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], embedding: np.ndarray | None = None) -> HippoRAGNode:
        """Create from dictionary."""
        return cls(
            node_id=data.get("node_id", str(uuid4())),
            content=data.get("content", ""),
            node_type=data.get("node_type", NodeType.PHRASE),
            embedding=embedding,
            source_passage_id=data.get("source_passage_id"),
            metadata=data.get("metadata", {}),
        )

    def is_phrase(self) -> bool:
        """Check if this is a phrase node."""
        return self.node_type == NodeType.PHRASE

    def is_passage(self) -> bool:
        """Check if this is a passage node."""
        return self.node_type == NodeType.PASSAGE


class HippoRAGMixin:
    """
    Mixin for GraphMemoryCollection to support HippoRAG node type distinction.

    Provides:
    - Phrase vs Passage node distinction
    - Contains edges (passage -> phrase)
    - Synonym edge management
    - Node type filtering in retrieval
    """

    def insert_phrase_node(
        self,
        phrase: str,
        source_passage_id: str | None = None,
        vector: np.ndarray | None = None,
        index_name: str = "default",
        node_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Insert a phrase node (entity/concept).

        Args:
            phrase: The phrase/entity text
            source_passage_id: ID of source passage (creates contains edge)
            vector: Embedding vector
            index_name: Target index name
            node_id: Optional node ID
            **kwargs: Additional metadata

        Returns:
            Node ID
        """
        metadata = {
            "node_type": NodeType.PHRASE,
            "source_passage_id": source_passage_id,
            **kwargs,
        }

        nid = self.insert(  # type: ignore[attr-defined]
            content=phrase,
            index_names=index_name,
            vector=vector,
            metadata=metadata,
            node_id=node_id or str(uuid4()),
        )

        # Create contains edge from passage to phrase
        if source_passage_id and hasattr(self, "add_edge"):
            self.add_edge(  # type: ignore[attr-defined]
                source_passage_id,
                nid,
                weight=1.0,
                index_name=index_name,
            )

        return nid

    def insert_passage_node(
        self,
        passage: str,
        vector: np.ndarray | None = None,
        index_name: str = "default",
        node_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Insert a passage node (original document).

        Args:
            passage: The passage text
            vector: Embedding vector
            index_name: Target index name
            node_id: Optional node ID
            **kwargs: Additional metadata

        Returns:
            Node ID
        """
        metadata = {
            "node_type": NodeType.PASSAGE,
            **kwargs,
        }

        return self.insert(  # type: ignore[attr-defined]
            content=passage,
            index_names=index_name,
            vector=vector,
            metadata=metadata,
            node_id=node_id or str(uuid4()),
        )

    def add_contains_edge(
        self,
        passage_id: str,
        phrase_id: str,
        weight: float = 1.0,
        index_name: str = "default",
    ) -> bool:
        """
        Add a contains edge from passage to phrase.

        Args:
            passage_id: Passage node ID
            phrase_id: Phrase node ID
            weight: Edge weight
            index_name: Graph index name

        Returns:
            True if edge added successfully
        """
        if not hasattr(self, "add_edge"):
            return False

        # Update phrase metadata
        if hasattr(self, "metadata_storage"):
            metadata = self.metadata_storage.get(phrase_id) or {}  # type: ignore[attr-defined]
            metadata["source_passage_id"] = passage_id
            self.metadata_storage.store(phrase_id, metadata)  # type: ignore[attr-defined]

        self.add_edge(passage_id, phrase_id, weight, index_name)  # type: ignore[attr-defined]
        return True

    def add_synonym_edge(
        self,
        phrase_id_1: str,
        phrase_id_2: str,
        weight: float = 1.0,
        index_name: str = "default",
    ) -> bool:
        """
        Add a synonym edge between two phrase nodes.

        Args:
            phrase_id_1: First phrase node ID
            phrase_id_2: Second phrase node ID
            weight: Edge weight (similarity score)
            index_name: Graph index name

        Returns:
            True if edge added successfully
        """
        if not hasattr(self, "add_edge"):
            return False

        # Bidirectional synonym edge
        self.add_edge(phrase_id_1, phrase_id_2, weight, index_name)  # type: ignore[attr-defined]
        self.add_edge(phrase_id_2, phrase_id_1, weight, index_name)  # type: ignore[attr-defined]
        return True

    def retrieve_by_node_type(
        self,
        node_type: str,
        top_k: int = 10,
        query_vector: np.ndarray | None = None,
        index_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve nodes of a specific type.

        Args:
            node_type: "phrase" or "passage"
            top_k: Number of results
            query_vector: Optional query vector for ranking
            index_name: Index to search

        Returns:
            List of matching nodes
        """

        def type_filter(m: dict[str, Any]) -> bool:
            return m.get("node_type") == node_type

        return self.retrieve(  # type: ignore[attr-defined]
            query=query_vector,
            index_name=index_name,
            top_k=top_k,
            with_metadata=True,
            metadata_filter=type_filter,
        )

    def get_passage_phrases(self, passage_id: str, index_name: str = "default") -> list[str]:
        """
        Get all phrase IDs contained in a passage.

        Args:
            passage_id: Passage node ID
            index_name: Graph index name

        Returns:
            List of phrase node IDs
        """
        if not hasattr(self, "get_neighbors"):
            return []

        neighbors = self.get_neighbors(passage_id, k=100, index_name=index_name)  # type: ignore[attr-defined]
        phrase_ids = []

        for neighbor in neighbors:
            neighbor_id = neighbor.get("node_id") if isinstance(neighbor, dict) else neighbor[0]
            if hasattr(self, "metadata_storage"):
                meta = self.metadata_storage.get(neighbor_id)  # type: ignore[attr-defined]
                if meta and meta.get("node_type") == NodeType.PHRASE:
                    phrase_ids.append(neighbor_id)

        return phrase_ids


# =============================================================================
# 5.8 Mem0g Graph-Enhanced Version
# =============================================================================


@dataclass
class Mem0gEntity:
    """An entity in Mem0g directed labeled graph."""

    entity_id: str
    entity_type: str  # e.g., "PERSON", "ORGANIZATION", etc.
    name: str
    embedding: np.ndarray | None = None
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], embedding: np.ndarray | None = None) -> Mem0gEntity:
        """Create from dictionary."""
        return cls(
            entity_id=data.get("entity_id", str(uuid4())),
            entity_type=data.get("entity_type", "UNKNOWN"),
            name=data.get("name", ""),
            embedding=embedding,
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Mem0gRelation:
    """A relation (edge) in Mem0g directed labeled graph."""

    source_id: str
    relation_type: str  # e.g., "works_at", "lives_in"
    target_id: str
    valid: bool = True  # Supports logical deletion
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_id": self.source_id,
            "relation_type": self.relation_type,
            "target_id": self.target_id,
            "valid": self.valid,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Mem0gRelation:
        """Create from dictionary."""
        return cls(
            source_id=data.get("source_id", ""),
            relation_type=data.get("relation_type", "related_to"),
            target_id=data.get("target_id", ""),
            valid=data.get("valid", True),
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata", {}),
        )

    def get_key(self) -> tuple[str, str, str]:
        """Get unique key for this relation."""
        return (self.source_id, self.relation_type, self.target_id)


class Mem0gMixin:
    """
    Mixin for GraphMemoryCollection to support Mem0g (graph-enhanced Mem0).

    Provides:
    - Entity management with types
    - Labeled directed edges (relations)
    - Logical deletion (valid flag)
    - Entity-centric retrieval
    """

    _mem0g_entities: dict[str, Mem0gEntity]
    _mem0g_relations: dict[tuple[str, str, str], Mem0gRelation]

    def _ensure_mem0g_storage(self) -> None:
        """Ensure Mem0g storage is initialized."""
        if not hasattr(self, "_mem0g_entities"):
            self._mem0g_entities = {}
        if not hasattr(self, "_mem0g_relations"):
            self._mem0g_relations = {}

    def add_entity(
        self,
        name: str,
        entity_type: str,
        vector: np.ndarray | None = None,
        index_name: str = "default",
        entity_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Add an entity to the graph.

        Args:
            name: Entity name
            entity_type: Entity type (PERSON, ORG, etc.)
            vector: Embedding vector
            index_name: Graph index name
            entity_id: Optional entity ID
            **kwargs: Additional metadata

        Returns:
            Entity ID
        """
        self._ensure_mem0g_storage()

        entity = Mem0gEntity(
            entity_id=entity_id or str(uuid4()),
            entity_type=entity_type,
            name=name,
            embedding=vector,
            metadata=kwargs,
        )

        self._mem0g_entities[entity.entity_id] = entity

        # Also insert to graph collection
        metadata = {
            "entity_type": entity_type,
            "mem0g_entity": True,
            **kwargs,
        }

        self.insert(  # type: ignore[attr-defined]
            content=name,
            index_names=index_name,
            vector=vector,
            metadata=metadata,
            node_id=entity.entity_id,
        )

        return entity.entity_id

    def add_relation(
        self,
        source_id: str,
        relation_type: str,
        target_id: str,
        index_name: str = "default",
        **kwargs: Any,
    ) -> bool:
        """
        Add a labeled relation between entities.

        Args:
            source_id: Source entity ID
            relation_type: Relation label
            target_id: Target entity ID
            index_name: Graph index name
            **kwargs: Additional metadata

        Returns:
            True if relation added successfully
        """
        self._ensure_mem0g_storage()

        relation = Mem0gRelation(
            source_id=source_id,
            relation_type=relation_type,
            target_id=target_id,
            metadata=kwargs,
        )

        self._mem0g_relations[relation.get_key()] = relation

        # Add edge to graph
        if hasattr(self, "add_edge"):
            self.add_edge(source_id, target_id, weight=1.0, index_name=index_name)  # type: ignore[attr-defined]

        return True

    def invalidate_relation(
        self,
        source_id: str,
        relation_type: str,
        target_id: str,
    ) -> bool:
        """
        Logically delete a relation (set valid=False).

        Args:
            source_id: Source entity ID
            relation_type: Relation label
            target_id: Target entity ID

        Returns:
            True if relation was invalidated
        """
        self._ensure_mem0g_storage()

        key = (source_id, relation_type, target_id)
        if key in self._mem0g_relations:
            self._mem0g_relations[key].valid = False
            return True
        return False

    def get_entity(self, entity_id: str) -> Mem0gEntity | None:
        """Get an entity by ID."""
        self._ensure_mem0g_storage()
        return self._mem0g_entities.get(entity_id)

    def get_entity_relations(
        self,
        entity_id: str,
        direction: str = "outgoing",
        include_invalid: bool = False,
    ) -> list[Mem0gRelation]:
        """
        Get relations for an entity.

        Args:
            entity_id: Entity ID
            direction: "outgoing", "incoming", or "both"
            include_invalid: Include logically deleted relations

        Returns:
            List of relations
        """
        self._ensure_mem0g_storage()

        relations = []
        for _key, rel in self._mem0g_relations.items():
            if not include_invalid and not rel.valid:
                continue

            if (
                direction == "outgoing"
                and rel.source_id == entity_id
                or direction == "incoming"
                and rel.target_id == entity_id
                or direction == "both"
                and (rel.source_id == entity_id or rel.target_id == entity_id)
            ):
                relations.append(rel)

        return relations

    def get_entities_by_type(self, entity_type: str) -> list[Mem0gEntity]:
        """Get all entities of a specific type."""
        self._ensure_mem0g_storage()
        return [e for e in self._mem0g_entities.values() if e.entity_type == entity_type]

    def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        top_k: int = 10,
    ) -> list[Mem0gEntity]:
        """
        Search entities by name.

        Args:
            query: Search query
            entity_type: Optional type filter
            top_k: Number of results

        Returns:
            List of matching entities
        """
        self._ensure_mem0g_storage()

        query_lower = query.lower()
        matches = []

        for entity in self._mem0g_entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            if query_lower in entity.name.lower():
                matches.append(entity)

        return matches[:top_k]

    # --- Persistence ---

    def save_mem0g_state(self) -> dict[str, Any]:
        """Save Mem0g state for persistence."""
        self._ensure_mem0g_storage()
        return {
            "entities": {eid: e.to_dict() for eid, e in self._mem0g_entities.items()},
            "relations": [r.to_dict() for r in self._mem0g_relations.values()],
        }

    def load_mem0g_state(self, data: dict[str, Any]) -> None:
        """Load Mem0g state from persistence."""
        self._ensure_mem0g_storage()
        if "entities" in data:
            self._mem0g_entities = {
                eid: Mem0gEntity.from_dict(e) for eid, e in data["entities"].items()
            }
        if "relations" in data:
            for r_data in data["relations"]:
                rel = Mem0gRelation.from_dict(r_data)
                self._mem0g_relations[rel.get_key()] = rel


# =============================================================================
# Convenience: Combined Mixin with all paper features
# =============================================================================


class PaperFeaturesMixin(
    TripleStorageMixin,
    ForgettingMixin,
    HeatMigrationMixin,
    TokenBudgetMixin,
    ConflictDetectionMixin,
):
    """
    Combined mixin with all paper features for VDB collections.

    Includes:
    - Triple storage (TiM)
    - Ebbinghaus forgetting (MemoryBank)
    - Heat-based migration (MemoryBank)
    - Token budget filtering (SCM)
    - Conflict detection (Mem0)
    """


class GraphPaperFeaturesMixin(
    AMemNoteMixin,
    LinkEvolutionMixin,
    ForgettingMixin,
    HeatMigrationMixin,
    HippoRAGMixin,
    Mem0gMixin,
):
    """
    Combined mixin with paper features for Graph collections.

    Includes:
    - Note structure (A-Mem)
    - Link evolution (A-Mem)
    - Ebbinghaus forgetting (MemoryBank)
    - Heat-based migration (MemoryBank)
    - Phrase/Passage node distinction (HippoRAG)
    - Graph-enhanced memory (Mem0g)
    """


class HierarchicalPaperFeaturesMixin(
    UserPortraitMixin,
    MemGPTStorageMixin,
    SegmentPageMixin,
    LPMMixin,
    HeatMigrationMixin,
):
    """
    Combined mixin with paper features for Hierarchical memory services.

    Includes:
    - User portrait (MemoryBank)
    - Three-tier storage (MemGPT)
    - Segment-Page architecture (MemoryOS)
    - Long-term Personal Memory (MemoryOS)
    - Heat-based migration (MemoryOS)
    """
