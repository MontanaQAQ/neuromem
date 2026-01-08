"""
Unit tests for Paper Features with UnifiedCollection (Week 2.2).

这是 test_paper_features.py 的重构版本，使用 UnifiedCollection + Mixin 替代 legacy enhanced collections。

Tests for:
- 5.1 Triple Storage (TiM)
- 5.2 Link Evolution (A-Mem)
- 5.3 Ebbinghaus Forgetting (MemoryBank)
- 5.4 Heat Score Migration (MemoryOS)
- 5.5 Token Budget (SCM)
- 5.6 Conflict Detection (Mem0)
"""

import time

import numpy as np
import pytest

from sage.neuromem.memory_collection.collections_with_features import (
    UnifiedCollectionWithGraphFeatures,
    UnifiedCollectionWithVDBFeatures,
)
from sage.neuromem.memory_collection.paper_features import (
    # 5.6 Conflict Detection
    ConflictConfig,
    ConflictDetector,
    EbbinghausForgetting,
    EntityAttributeExtractor,
    ForgettingConfig,
    HeatConfig,
    HeatScoreManager,
    # 5.2 Link Evolution
    SimpleTokenCounter,
    TokenBudgetConfig,
    TokenBudgetFilter,
    Triple,
)

# =============================================================================
# 5.1 Triple Storage Tests
# =============================================================================


class TestTriple:
    """Tests for Triple dataclass."""

    def test_triple_creation(self):
        """Test basic triple creation."""
        triple = Triple(
            query="What is the capital of France?",
            passage="Paris is the capital and largest city of France.",
            answer="Paris",
        )
        assert triple.query == "What is the capital of France?"
        assert triple.passage == "Paris is the capital and largest city of France."
        assert triple.answer == "Paris"

    def test_triple_to_json(self):
        """Test triple serialization."""
        triple = Triple(
            query="What is 2+2?",
            passage="Basic arithmetic.",
            answer="4",
        )
        json_str = triple.to_json()
        assert "query" in json_str
        assert "passage" in json_str
        assert "answer" in json_str

    def test_triple_from_json(self):
        """Test triple deserialization."""
        triple = Triple(
            query="Test query",
            passage="Test passage",
            answer="Test answer",
        )
        json_str = triple.to_json()
        restored = Triple.from_json(json_str)

        assert restored.query == triple.query
        assert restored.passage == triple.passage
        assert restored.answer == triple.answer

    def test_triple_hashes(self):
        """Test hash generation."""
        triple = Triple(query="q1", passage="p1", answer="a1")
        query_hash = triple.get_query_hash()
        passage_hash = triple.get_passage_hash()

        assert len(query_hash) == 8
        assert len(passage_hash) == 8
        assert query_hash != passage_hash


class TestTripleStorageMixin:
    """Tests for TripleStorageMixin."""

    def test_insert_triple(self):
        """Test inserting a triple."""
        collection = UnifiedCollectionWithVDBFeatures("test_triple")
        collection.add_index("triple_index", "faiss", {"dim": 4})

        vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        item_id = collection.insert_triple(
            query="What is Python?",
            passage="Python is a programming language.",
            answer="A programming language",
            vector=vector,
            index_name="triple_index",
        )

        assert item_id is not None
        assert len(item_id) == 64  # SHA256 hex digest

    def test_retrieve_triples(self):
        """Test retrieving triples."""
        collection = UnifiedCollectionWithVDBFeatures({"name": "test_retrieve_triple"})
        collection.add_index("triple_index", "faiss", {"dim": 4})

        # Insert some triples
        vectors = [
            np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            np.array([0.2, 0.3, 0.4, 0.5], dtype=np.float32),
        ]
        collection.insert_triple(
            query="What is Python?",
            passage="Python is a programming language.",
            answer="A programming language",
            vector=vectors[0],
        )
        collection.insert_triple(
            query="What is Java?",
            passage="Java is also a programming language.",
            answer="A programming language",
            vector=vectors[1],
        )

        # Retrieve
        query_vector = np.array([0.15, 0.25, 0.35, 0.45], dtype=np.float32)
        results = collection.retrieve_triples(
            query_vector=query_vector,
            index_name="triple_index",
            top_k=2,
        )

        assert len(results) >= 1
        assert "query" in results[0]
        assert "passage" in results[0]
        assert "answer" in results[0]
        assert "score" in results[0]


# =============================================================================
# 5.2 Link Evolution Tests
# =============================================================================


class TestLinkEvolutionMixin:
    """Tests for LinkEvolutionMixin."""

    def test_evolve_links_decay(self):
        """Test edge weight decay."""
        collection = UnifiedCollectionWithGraphFeatures({"name": "test_evolve"})
        collection.add_index("default", "graph", {})

        # Add nodes and edges
        collection.insert(content="Node A", index_names="default", node_id="A")
        collection.insert(content="Node B", index_names="default", node_id="B")
        collection.add_edge("A", "B", weight=1.0, index_name="default")

        # Evolve with decay
        updated = collection.evolve_links(
            node_id="A",
            index_name="default",
            decay_factor=0.5,
        )

        assert updated >= 1

        # Check weight was decayed
        weight = collection.indexes["default"].get_edge_weight("A", "B")
        assert weight is not None
        assert weight < 1.0

    def test_batch_evolve_links(self):
        """Test batch evolution."""
        collection = UnifiedCollectionWithGraphFeatures({"name": "test_batch_evolve"})
        collection.add_index("default", "graph", {})

        # Add nodes
        for i in range(3):
            collection.insert(
                content=f"Node {i}",
                index_names="default",
                node_id=str(i),
            )

        # Add edges
        collection.add_edge("0", "1", weight=1.0, index_name="default")
        collection.add_edge("1", "2", weight=1.0, index_name="default")

        # Batch evolve
        total_updated = collection.batch_evolve_links(
            index_name="default",
            decay_factor=0.9,
        )

        assert total_updated >= 2


# =============================================================================
# 5.3 Ebbinghaus Forgetting Tests
# =============================================================================


class TestEbbinghausForgetting:
    """Tests for EbbinghausForgetting."""

    def test_calculate_strength_fresh(self):
        """Test strength calculation for fresh memory."""
        forgetting = EbbinghausForgetting()
        current_time = time.time()

        strength = forgetting.calculate_strength(
            last_access_time=current_time,  # Just accessed
            access_count=0,
            current_time=current_time,
        )

        # Fresh memory should have high strength
        assert strength >= 0.7

    def test_calculate_strength_old(self):
        """Test strength calculation for old memory."""
        forgetting = EbbinghausForgetting()
        current_time = time.time()

        strength = forgetting.calculate_strength(
            last_access_time=current_time - 24 * 3600,  # 24 hours ago
            access_count=0,
            current_time=current_time,
        )

        # Old unused memory should have low strength
        assert strength < 0.3

    def test_reinforcement(self):
        """Test access count reinforcement."""
        forgetting = EbbinghausForgetting()
        current_time = time.time()

        # Same time, different access counts
        strength_low = forgetting.calculate_strength(
            last_access_time=current_time - 12 * 3600,
            access_count=0,
            current_time=current_time,
        )
        strength_high = forgetting.calculate_strength(
            last_access_time=current_time - 12 * 3600,
            access_count=10,
            current_time=current_time,
        )

        # More access should mean higher strength
        assert strength_high > strength_low

    def test_should_forget(self):
        """Test forgetting decision."""
        config = ForgettingConfig(strength_threshold=0.4)
        forgetting = EbbinghausForgetting(config)
        current_time = time.time()

        # Fresh memory
        metadata_fresh = {
            "last_access_time": current_time,
            "access_count": 5,
        }
        assert not forgetting.should_forget(metadata_fresh, current_time)

        # Old memory
        metadata_old = {
            "last_access_time": current_time - 48 * 3600,
            "access_count": 0,
        }
        assert forgetting.should_forget(metadata_old, current_time)


class TestForgettingMixin:
    """Tests for ForgettingMixin."""

    def test_update_access(self):
        """Test access update."""
        collection = UnifiedCollectionWithVDBFeatures({"name": "test_access"})
        collection.add_index("main", "faiss", {"dim": 4})

        # Insert item
        vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        item_id = collection.insert(
            content="Test content",
            index_names="main",
            vector=vector,
            metadata={"access_count": 0},
        )

        # Update access
        result = collection.update_access(item_id)
        assert result is True

        # Check metadata updated
        metadata = collection.get_metadata(item_id)
        assert metadata is not None
        assert metadata.get("access_count", 0) >= 1
        assert "last_access_time" in metadata

    def test_apply_forgetting(self):
        """Test forgetting application."""
        collection = UnifiedCollectionWithVDBFeatures({"name": "test_forget"})
        collection.add_index("main", "faiss", {"dim": 4})

        current_time = time.time()

        # Insert fresh item
        fresh_vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        fresh_id = collection.insert(
            content="Fresh content",
            index_names="main",
            vector=fresh_vector,
            metadata={
                "last_access_time": current_time,
                "access_count": 5,
            },
        )

        # Insert old item
        old_vector = np.array([0.5, 0.6, 0.7, 0.8], dtype=np.float32)
        old_id = collection.insert(
            content="Old content",
            index_names="main",
            vector=old_vector,
            metadata={
                "last_access_time": current_time - 72 * 3600,  # 72 hours ago
                "access_count": 0,
            },
        )

        # Apply forgetting
        config = ForgettingConfig(strength_threshold=0.3)
        forgetting = EbbinghausForgetting(config)
        forgotten = collection.apply_forgetting(forgetting, current_time)

        # Old item should be forgotten
        assert old_id in forgotten
        assert fresh_id not in forgotten

        # Verify deletion (text_storage.get returns "" for deleted items)
        assert not collection.has_item(old_id)
        assert collection.has_item(fresh_id)


# =============================================================================
# 5.4 Heat Score Tests
# =============================================================================


class TestHeatScoreManager:
    """Tests for HeatScoreManager."""

    def test_calculate_heat_hot(self):
        """Test heat calculation for hot memory."""
        manager = HeatScoreManager()
        current_time = time.time()

        heat = manager.calculate_heat(
            access_count=100,
            last_access_time=current_time,  # Just accessed
            creation_time=current_time - 3600,  # 1 hour old
            current_time=current_time,
        )

        assert heat > 0.5

    def test_calculate_heat_cold(self):
        """Test heat calculation for cold memory."""
        manager = HeatScoreManager()
        current_time = time.time()

        heat = manager.calculate_heat(
            access_count=0,
            last_access_time=current_time - 48 * 3600,  # 48 hours ago
            creation_time=current_time - 72 * 3600,  # 72 hours old
            current_time=current_time,
        )

        assert heat < 0.3

    def test_migration_actions(self):
        """Test migration action determination."""
        config = HeatConfig(cold_threshold=0.3, hot_threshold=0.8)
        manager = HeatScoreManager(config)

        assert manager.get_migration_action(0.1) == "demote"
        assert manager.get_migration_action(0.5) is None
        assert manager.get_migration_action(0.9) == "promote"


# =============================================================================
# 5.5 Token Budget Tests
# =============================================================================


class TestSimpleTokenCounter:
    """Tests for SimpleTokenCounter."""

    def test_count_tokens(self):
        """Test token counting."""
        counter = SimpleTokenCounter(chars_per_token=4.0)

        assert counter.count("hello") == 1  # 5 chars / 4 = 1
        assert counter.count("hello world test") == 4  # 16 chars / 4 = 4


class TestTokenBudgetFilter:
    """Tests for TokenBudgetFilter."""

    def test_filter_by_budget(self):
        """Test budget filtering."""
        config = TokenBudgetConfig(
            default_budget=100,
            reserve_tokens=10,
            chars_per_token=4.0,
        )
        filter_ = TokenBudgetFilter(config=config)

        items = [
            {"text": "a" * 100, "score": 1.0},  # 25 tokens
            {"text": "b" * 100, "score": 0.9},  # 25 tokens
            {"text": "c" * 100, "score": 0.8},  # 25 tokens
            {"text": "d" * 100, "score": 0.7},  # 25 tokens
        ]

        # Budget is 100 - 10 = 90 tokens
        # Should fit 3 items (75 tokens)
        filtered = filter_.filter_by_budget(items, budget=100)
        assert len(filtered) == 3

    def test_budget_utilization(self):
        """Test utilization stats."""
        filter_ = TokenBudgetFilter()

        items = [
            {"text": "hello world", "score": 1.0},
            {"text": "test message", "score": 0.9},
        ]

        stats = filter_.get_budget_utilization(items, budget=100)

        assert "total_items" in stats
        assert "total_tokens" in stats
        assert "utilization" in stats
        assert stats["total_items"] == 2


class TestTokenBudgetMixin:
    """Tests for TokenBudgetMixin."""

    def test_retrieve_with_budget(self):
        """Test retrieval with budget."""
        collection = UnifiedCollectionWithVDBFeatures({"name": "test_budget"})
        collection.add_index("main", "faiss", {"dim": 4})

        # Insert items with varying text lengths
        for i in range(5):
            vector = np.random.rand(4).astype(np.float32)
            collection.insert(
                content="x" * (100 * (i + 1)),  # Increasing lengths
                index_names="main",
                vector=vector,
            )

        # Retrieve with budget
        query = np.random.rand(4).astype(np.float32)
        results = collection.retrieve_with_budget(
            query=query,
            index_name="main",
            token_budget=200,  # Small budget
            max_candidates=10,
        )

        # Should have fewer results due to budget
        assert len(results) < 5


# =============================================================================
# 5.6 Conflict Detection Tests
# =============================================================================


class TestEntityAttributeExtractor:
    """Tests for EntityAttributeExtractor."""

    def test_extract_possessive(self):
        """Test possessive pattern extraction."""
        extractor = EntityAttributeExtractor()

        result = extractor.extract("John's age is 25")
        assert result is not None
        entity, attribute, value = result
        assert entity == "John"
        assert attribute == "age"
        assert value == "25"

    def test_extract_has_pattern(self):
        """Test 'has' pattern extraction."""
        extractor = EntityAttributeExtractor()

        result = extractor.extract("The company has revenue 1 million")
        assert result is not None

    def test_get_key(self):
        """Test entity-attribute key extraction."""
        extractor = EntityAttributeExtractor()

        key = extractor.get_entity_attribute_key("John's age is 25")
        assert key == ("John", "age")

        # Non-matching text
        key = extractor.get_entity_attribute_key("Random text without pattern")
        assert key is None


class TestConflictDetector:
    """Tests for ConflictDetector."""

    def test_detect_entity_attribute_conflict(self):
        """Test entity-attribute conflict detection."""
        detector = ConflictDetector()

        new_fact = "John's age is 30"
        existing_facts = [
            {"text": "John's age is 25", "id": "old_fact"},
        ]

        result = detector.detect(new_fact, existing_facts)

        assert result.has_conflict is True
        assert result.conflict_type == "entity_attribute"
        assert result.conflicting_item is not None

    def test_no_conflict(self):
        """Test no conflict case."""
        detector = ConflictDetector()

        new_fact = "Mary's age is 30"
        existing_facts = [
            {"text": "John's age is 25", "id": "old_fact"},
        ]

        result = detector.detect(new_fact, existing_facts)
        assert result.has_conflict is False

    def test_semantic_conflict(self):
        """Test semantic conflict detection."""
        config = ConflictConfig(semantic_threshold=0.9)
        detector = ConflictDetector(config)

        # Create similar vectors
        new_vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        existing_vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

        new_fact = "Some fact"
        existing_facts = [
            {"text": "Similar fact", "id": "existing"},
        ]

        def get_vector(_text: str) -> np.ndarray:
            return existing_vector

        result = detector.detect(
            new_fact,
            existing_facts,
            new_vector=new_vector,
            get_vector_func=get_vector,
        )

        assert result.has_conflict is True
        assert result.conflict_type == "semantic"
        assert result.similarity > 0.9


class TestConflictDetectionMixin:
    """Tests for ConflictDetectionMixin."""

    def test_insert_with_conflict_skip(self):
        """Test insert with conflict - skip resolution."""
        collection = UnifiedCollectionWithVDBFeatures({"name": "test_conflict"})
        collection.add_index("main", "faiss", {"dim": 4})

        vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

        # Insert first fact
        collection.insert(
            content="John's age is 25",
            index_names="main",
            vector=vector,
        )

        # Try to insert conflicting fact
        result = collection.insert_with_conflict_check(
            content="John's age is 30",
            vector=vector,
            index_name="main",
            resolution="skip",
        )

        assert result["action"] == "skipped"
        assert result["id"] is None
        assert result["conflict"] is not None

    def test_insert_with_conflict_replace(self):
        """Test insert with conflict - replace resolution."""
        collection = UnifiedCollectionWithVDBFeatures({"name": "test_replace"})
        collection.add_index("main", "faiss", {"dim": 4})

        vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

        # Insert first fact
        old_id = collection.insert(
            content="John's age is 25",
            index_names="main",
            vector=vector,
        )

        # Insert conflicting fact with replace
        result = collection.insert_with_conflict_check(
            content="John's age is 30",
            vector=vector,
            index_name="main",
            resolution="replace",
        )

        assert result["action"] == "replaced"
        assert result["id"] is not None
        assert result["conflict"] is not None

        # Old item should be deleted (has_item returns False)
        assert not collection.has_item(old_id)

    def test_insert_no_conflict(self):
        """Test insert without conflict."""
        collection = UnifiedCollectionWithVDBFeatures({"name": "test_no_conflict"})
        collection.add_index("main", "faiss", {"dim": 4})

        vector1 = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        vector2 = np.array([0.5, 0.6, 0.7, 0.8], dtype=np.float32)

        # Insert first fact
        collection.insert(
            content="John's age is 25",
            index_names="main",
            vector=vector1,
        )

        # Insert non-conflicting fact
        result = collection.insert_with_conflict_check(
            content="Mary's age is 30",
            vector=vector2,
            index_name="main",
        )

        assert result["action"] == "inserted"
        assert result["id"] is not None
        assert result["conflict"] is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestEnhancedVDBCollection:
    """Integration tests for UnifiedCollectionWithVDBFeatures."""

    def test_all_features_available(self):
        """Test that all paper features are available."""
        collection = UnifiedCollectionWithVDBFeatures({"name": "test_all"})

        # Check methods exist
        assert hasattr(collection, "insert_triple")
        assert hasattr(collection, "retrieve_triples")
        assert hasattr(collection, "update_access")
        assert hasattr(collection, "apply_forgetting")
        assert hasattr(collection, "get_all_heat_scores")
        assert hasattr(collection, "retrieve_with_budget")
        assert hasattr(collection, "insert_with_conflict_check")


class TestEnhancedGraphCollection:
    """Integration tests for UnifiedCollectionWithGraphFeatures."""

    def test_all_features_available(self):
        """Test that all paper features are available."""
        collection = UnifiedCollectionWithGraphFeatures({"name": "test_all"})

        # Check methods exist
        assert hasattr(collection, "evolve_links")
        assert hasattr(collection, "batch_evolve_links")
        assert hasattr(collection, "update_access")
        assert hasattr(collection, "apply_forgetting")
        assert hasattr(collection, "get_all_heat_scores")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
