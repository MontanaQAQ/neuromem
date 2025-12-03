"""
Paper-specific features for NeuroMem Collections.

This module implements features from various memory-augmented LLM papers:
- TiM: Triple storage (query, passage, answer)
- A-Mem: Link evolution based on similarity
- MemoryBank: Ebbinghaus forgetting curve
- MemoryOS: Heat score based tier migration
- SCM: Token budget filtering
- Mem0: Conflict detection

These are designed as composable utilities that can be used with any Collection.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable


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
        vector: np.ndarray,
        index_name: str = "triple_index",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Insert a triple into the collection.

        Args:
            query: The query text
            passage: The passage text (used for embedding)
            answer: The answer text
            vector: Pre-computed embedding vector (based on passage)
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
        current_neighbors = graph_index.get_neighbors(node_id, k=100)
        for neighbor_id, weight in current_neighbors:
            new_weight = weight * decay_factor
            if new_weight < min_weight:
                graph_index.remove_edge(node_id, neighbor_id)
            else:
                graph_index.update_edge_weight(node_id, neighbor_id, new_weight)
            updated_count += 1

        # 3. Add/strengthen edges to similar nodes
        for neighbor_id, similarity in similar_nodes:
            if neighbor_id == node_id:
                continue
            if similarity < similarity_threshold:
                continue

            if graph_index.has_edge(node_id, neighbor_id):
                # Strengthen existing edge
                current_weight = graph_index.get_edge_weight(node_id, neighbor_id) or 0.0
                new_weight = min(current_weight + similarity * reinforcement_factor, max_weight)
                graph_index.update_edge_weight(node_id, neighbor_id, new_weight)
            else:
                # Add new edge
                graph_index.add_edge(node_id, neighbor_id, similarity)

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
        elif heat > self.config.hot_threshold:
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
        content: str,
        vector: np.ndarray,
        index_name: str,
        detector: ConflictDetector | None = None,
        resolution: str = "skip",  # "skip", "replace", "append"
        metadata: dict[str, Any] | None = None,
        get_vector_func: Callable[[str], np.ndarray | None] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Insert with conflict detection.

        Args:
            content: Text content
            vector: Content vector
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
        if (
            not hasattr(self, "retrieve")
            or not hasattr(self, "insert")
            or not hasattr(self, "delete")
        ):
            return {"id": None, "action": "error", "conflict": None}

        detector = detector or ConflictDetector()

        # Retrieve similar items for conflict check
        similar_items = self.retrieve(  # type: ignore[attr-defined]
            query=vector,
            index_name=index_name,
            top_k=10,
            with_metadata=True,
        )

        # Detect conflicts
        conflict_result = detector.detect(
            new_fact=content,
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

            elif resolution == "replace":
                # Delete old, insert new
                if conflict_item and "id" in conflict_item:
                    self.delete(conflict_item["id"])  # type: ignore[attr-defined]

                new_id = self.insert(  # type: ignore[attr-defined]
                    content=content,
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
        new_id = self.insert(  # type: ignore[attr-defined]
            content=content,
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
# Convenience: Combined Mixin with all paper features
# =============================================================================


class PaperFeaturesMixin(
    TripleStorageMixin,
    ForgettingMixin,
    TokenBudgetMixin,
    ConflictDetectionMixin,
):
    """
    Combined mixin with all paper features for VDB collections.

    Includes:
    - Triple storage (TiM)
    - Ebbinghaus forgetting (MemoryBank)
    - Token budget filtering (SCM)
    - Conflict detection (Mem0)
    """

    pass


class GraphPaperFeaturesMixin(
    LinkEvolutionMixin,
    ForgettingMixin,
):
    """
    Combined mixin with paper features for Graph collections.

    Includes:
    - Link evolution (A-Mem)
    - Ebbinghaus forgetting (MemoryBank)
    """

    pass
