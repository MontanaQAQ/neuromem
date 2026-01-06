"""
Unit tests for search_engine module - Part 2 refactoring.

Tests cover:
- SimpleGraphIndex: node/edge operations, neighbor queries, PPR
- BM25sIndex: search_with_sort, search_range
- IndexFactory: unified factory creation
"""

import tempfile

import pytest


class TestSimpleGraphIndex:
    """Tests for SimpleGraphIndex."""

    @pytest.fixture
    def graph_index(self):
        """Create a fresh graph index for each test."""
        from sage.neuromem.search_engine.graph_index import (
            SimpleGraphIndex,
        )

        return SimpleGraphIndex("test_graph")

    def test_add_node(self, graph_index):
        """Test adding nodes."""
        # Add new node
        assert graph_index.add_node("node1", {"text": "Hello"}) is True
        assert graph_index.has_node("node1") is True
        assert graph_index.get_node_data("node1") == {"text": "Hello"}

        # Adding same node again returns False (update)
        assert graph_index.add_node("node1", {"text": "Updated"}) is False
        assert graph_index.get_node_data("node1") == {"text": "Updated"}

    def test_remove_node(self, graph_index):
        """Test removing nodes."""
        graph_index.add_node("node1")
        graph_index.add_node("node2")
        graph_index.add_edge("node1", "node2")

        # Remove node1
        assert graph_index.remove_node("node1") is True
        assert graph_index.has_node("node1") is False
        # Edge should also be removed
        assert graph_index.has_edge("node1", "node2") is False

        # Try removing non-existent node
        assert graph_index.remove_node("node1") is False

    def test_add_edge_with_relation(self, graph_index):
        """Test adding edges with relation type."""
        graph_index.add_edge("a", "b", weight=0.8, relation="KNOWS")
        graph_index.add_edge("a", "c", weight=0.5, relation="WORKS_WITH")

        assert graph_index.has_edge("a", "b") is True
        assert graph_index.get_edge_weight("a", "b") == 0.8
        assert graph_index.get_edge_relation("a", "b") == "KNOWS"

    def test_update_edge_weight(self, graph_index):
        """Test updating edge weight."""
        graph_index.add_edge("a", "b", weight=0.5)
        assert graph_index.get_edge_weight("a", "b") == 0.5

        assert graph_index.update_edge_weight("a", "b", 0.9) is True
        assert graph_index.get_edge_weight("a", "b") == 0.9

        # Try updating non-existent edge
        assert graph_index.update_edge_weight("a", "x", 0.5) is False

    def test_get_neighbors_with_direction(self, graph_index):
        """Test getting neighbors with direction."""
        # Create graph: a -> b -> c, d -> b
        graph_index.add_edge("a", "b", weight=0.8)
        graph_index.add_edge("b", "c", weight=0.6)
        graph_index.add_edge("d", "b", weight=0.7)

        # Outgoing from b
        out_neighbors = graph_index.get_neighbors("b", k=10, direction="outgoing")
        assert len(out_neighbors) == 1
        assert out_neighbors[0][0] == "c"

        # Incoming to b
        in_neighbors = graph_index.get_neighbors("b", k=10, direction="incoming")
        assert len(in_neighbors) == 2
        neighbor_ids = [n[0] for n in in_neighbors]
        assert "a" in neighbor_ids
        assert "d" in neighbor_ids

        # Both directions
        all_neighbors = graph_index.get_neighbors("b", k=10, direction="both")
        assert len(all_neighbors) == 3

    def test_get_edges_by_relation(self, graph_index):
        """Test filtering edges by relation."""
        graph_index.add_edge("a", "b", relation="KNOWS")
        graph_index.add_edge("a", "c", relation="WORKS_WITH")
        graph_index.add_edge("a", "d", relation="KNOWS")

        knows_neighbors = graph_index.get_edges_by_relation("a", "KNOWS")
        assert len(knows_neighbors) == 2
        neighbor_ids = [n[0] for n in knows_neighbors]
        assert "b" in neighbor_ids
        assert "d" in neighbor_ids

    def test_traverse_bfs(self, graph_index):
        """Test BFS traversal."""
        # Create a tree: a -> b, a -> c, b -> d, b -> e
        graph_index.add_edge("a", "b")
        graph_index.add_edge("a", "c")
        graph_index.add_edge("b", "d")
        graph_index.add_edge("b", "e")

        result = graph_index.traverse_bfs("a", max_depth=2)
        assert result[0] == "a"  # Start node first
        assert len(result) == 5

    def test_traverse_dfs(self, graph_index):
        """Test DFS traversal."""
        graph_index.add_edge("a", "b")
        graph_index.add_edge("a", "c")
        graph_index.add_edge("b", "d")

        result = graph_index.traverse_dfs("a", max_depth=2)
        assert result[0] == "a"

    def test_ppr(self, graph_index):
        """Test Personalized PageRank."""
        # Create a simple graph
        graph_index.add_edge("a", "b", weight=1.0)
        graph_index.add_edge("b", "c", weight=1.0)
        graph_index.add_edge("c", "a", weight=1.0)  # Cycle
        graph_index.add_edge("a", "d", weight=0.5)

        # PPR from seed node "a"
        result = graph_index.ppr(["a"], alpha=0.15, top_k=4)
        assert len(result) > 0
        # All nodes should have some score
        node_ids = [n[0] for n in result]
        assert "a" in node_ids

    def test_store_and_load(self, graph_index):
        """Test persistence."""
        graph_index.add_node("n1", {"text": "Node 1"})
        graph_index.add_node("n2", {"text": "Node 2"})
        graph_index.add_edge("n1", "n2", weight=0.5, relation="LINKED")

        # Store
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_index.store(tmpdir)

            # Load
            from sage.neuromem.search_engine.graph_index import (
                SimpleGraphIndex,
            )

            loaded = SimpleGraphIndex.load("test_graph", tmpdir)

            assert loaded.has_node("n1")
            assert loaded.has_node("n2")
            assert loaded.has_edge("n1", "n2")
            assert loaded.get_edge_weight("n1", "n2") == 0.5
            assert loaded.get_edge_relation("n1", "n2") == "LINKED"

    def test_statistics(self, graph_index):
        """Test node_count and edge_count."""
        graph_index.add_node("a")
        graph_index.add_node("b")
        graph_index.add_edge("a", "b")

        assert graph_index.node_count() == 2
        assert graph_index.edge_count() == 1
        assert set(graph_index.get_all_node_ids()) == {"a", "b"}


class TestBM25sIndexExtended:
    """Tests for new BM25sIndex methods."""

    @pytest.fixture
    def kv_index(self):
        """Create a BM25sIndex with test data."""
        from sage.neuromem.search_engine.kv_index import (
            BM25sIndex,
        )

        config = {"name": "test_kv", "language": "en"}
        index = BM25sIndex(config=config)
        index.build_index(
            texts=[
                "Python is a programming language",
                "Java is also a programming language",
                "Machine learning with Python",
                "Deep learning frameworks",
            ],
            ids=["doc1", "doc2", "doc3", "doc4"],
        )
        return index

    def test_search_with_scores(self, kv_index):
        """Test search_with_scores returns scores."""
        results = kv_index.search_with_scores("Python programming", topk=2)
        assert len(results) == 2
        # Results should be tuples of (id, score)
        for doc_id, score in results:
            assert isinstance(doc_id, str)
            assert isinstance(score, float)
            assert score >= 0

    def test_search_with_sort(self, kv_index):
        """Test search_with_sort with metadata sorting."""
        metadata = {
            "doc1": {"timestamp": 100, "priority": 1},
            "doc2": {"timestamp": 200, "priority": 2},
            "doc3": {"timestamp": 50, "priority": 3},
            "doc4": {"timestamp": 150, "priority": 1},
        }

        def get_metadata(doc_id):
            return metadata.get(doc_id, {})

        # Search with sort by timestamp descending
        results = kv_index.search_with_sort(
            "programming",
            topk=3,
            sort_by="timestamp",
            sort_order="desc",
            metadata_getter=get_metadata,
        )
        assert len(results) > 0

    def test_search_range(self, kv_index):
        """Test range query on metadata."""
        metadata = {
            "doc1": {"timestamp": 100},
            "doc2": {"timestamp": 200},
            "doc3": {"timestamp": 50},
            "doc4": {"timestamp": 150},
        }

        def get_metadata(doc_id):
            return metadata.get(doc_id, {})

        results = kv_index.search_range(
            field="timestamp",
            min_value=100,
            max_value=200,
            topk=10,
            metadata_getter=get_metadata,
        )
        # Should include doc1 (100), doc2 (200), doc4 (150)
        assert "doc1" in results
        assert "doc2" in results
        assert "doc4" in results
        assert "doc3" not in results  # timestamp=50 is out of range

    def test_count_and_get_all_ids(self, kv_index):
        """Test count and get_all_ids methods."""
        assert kv_index.count() == 4
        all_ids = kv_index.get_all_ids()
        assert set(all_ids) == {"doc1", "doc2", "doc3", "doc4"}


class TestIndexFactory:
    """Tests for unified IndexFactory."""

    def test_create_kv_index(self):
        """Test creating KV index via factory."""
        from sage.neuromem.search_engine import IndexFactory

        index = IndexFactory.create_kv_index(
            {
                "name": "test_kv",
                "index_type": "bm25s",
                "language": "en",
            }
        )
        assert index is not None
        assert index.name == "test_kv"

    def test_create_graph_index(self):
        """Test creating graph index via factory."""
        from sage.neuromem.search_engine import IndexFactory

        index = IndexFactory.create_graph_index(
            {
                "name": "test_graph",
                "index_type": "simple",
            }
        )
        assert index is not None
        assert index.name == "test_graph"

    def test_get_supported_types(self):
        """Test getting supported index types."""
        from sage.neuromem.search_engine import IndexFactory

        kv_types = IndexFactory.get_supported_kv_types()
        assert "bm25s" in kv_types

        graph_types = IndexFactory.get_supported_graph_types()
        assert "simple" in graph_types


class TestGraphIndexFactory:
    """Tests for GraphIndexFactory."""

    def test_create_and_load(self):
        """Test create and load via factory."""
        from sage.neuromem.search_engine.graph_index import (
            GraphIndexFactory,
        )

        index = GraphIndexFactory.create({"name": "factory_test", "index_type": "simple"})
        index.add_node("a", "data")
        index.add_edge("a", "b")

        with tempfile.TemporaryDirectory() as tmpdir:
            index.store(tmpdir)
            loaded = GraphIndexFactory.load("factory_test", tmpdir, "simple")
            assert loaded.has_node("a")
            assert loaded.has_edge("a", "b")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
