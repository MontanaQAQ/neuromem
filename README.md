![NeuroMem Logo](docs/assets/neuromem.png)

<h3 align="center">
Love grows from the smallest of memories ~
</h3>

<p align="center">
| <a href="docs/cn/README_cn.md"><b>中文文档</b></a> | <a href="https://intellistream.slack.com/"><b>Developer Slack</b></a> |
</p>

🔥 Welcome! NeuroMem is a subproject of [SAGE](https://github.com/intellistream/SAGE), dedicated to exploring memory systems for large language models.

## Owner & Contact

- Repository Owner: [@KimmoZAG](https://github.com/KimmoZAG) (RuiCheng / 张睿诚)
- Maintainer Contact: Please open an issue in this repo and mention `@KimmoZAG`.
- PyPI-related ownership and release contact follow the same owner/contact above.

---

## Getting Started

Install neuromem with `pip` :

```bash
pip install isage-neuromem
```

For development, clone the repo and use the provided quickstart script:

```bash
git clone https://github.com/intellistream/NeuroMem.git
cd neuromem
./quickstart.sh
```

This will set up a local development environment (virtualenv + dependencies) suitable for running tests and benchmarks. You can then:

- Explore examples in `examples/`
- Run the benchmark suite in `benchmarks/`
- Dive into the core implementation under `sage/neuromem/`



<!-- # isage-neuromem




**NeuroMem** is a brain-inspired memory management engine for SAGE (Structured AI Graph Engine). It provides flexible memory collection abstractions with support for vector databases, key-value stores, and graph structures, designed specifically for RAG (Retrieval-Augmented Generation) applications.

## Installation

### From PyPI

```bash
pip install isage-neuromem
```

### For Development

```bash
# Clone the repository
git clone https://github.com/intellistream/NeuroMem.git
cd NeuroMem

# Quick start (recommended)
./quickstart.sh

# Or manual installation
pip install -e .
pip install pre-commit  # For contributors
pre-commit install
```

## Quick Start

```python
from sage.neuromem import MemoryManager, UnifiedCollection

# Using MemoryManager (recommended for multiple collections)
manager = MemoryManager()
collection = manager.create_collection("my_collection")

# Or directly using UnifiedCollection
collection = UnifiedCollection(
    name="my_collection",
    storage_backend="memory"  # Memory, Redis, or SageDB
)

# Insert data
collection.insert("id1", {"text": "Hello, world!"})

# Create an index for search
collection.add_index({
    "name": "text_search",
    "index_type": "bm25"  # FAISS, BM25, Graph, FIFO, etc.
})

# Search
results = collection.retrieve("hello", top_k=5, index_name="text_search")
```

## Features

- **UnifiedCollection**: Single abstraction for all memory types
  - Multi-index support: FAISS (vectors), BM25 (text), Graph, FIFO, Segment
  - Flexible storage: Memory, Redis, SageDB
  - Unified insert/retrieve API

- **Collection Configuration**: YAML-based config management
  - Pre-configured templates for common use cases
  - Automatic parameter validation and conversion
  - See `COLLECTION_CONFIG_GUIDE.md` for details

- **Storage Flexibility**: Pluggable storage backends
  - In-memory storage for development
  - Redis for distributed deployments  
  - SageDB for large-scale vector storage

- **Paper Features**: Mixins for advanced memory techniques
  - Triple Storage, Link Evolution, Forgetting
  - Heat Score Migration, Token Budget
  - Conflict Detection, HippoRAG patterns, etc.

## Architecture

```
sage/neuromem/
├── memory_manager.py              # Central manager for collections
├── memory_collection/
│   ├── unified_collection.py      # Unified collection abstraction ⭐
│   ├── collection_config.py       # YAML configuration management
│   ├── indexes/                   # Index implementations
│   │   ├── faiss_index.py
│   │   ├── bm25_index.py
│   │   ├── graph_index.py
│   │   └── ...
│   └── paper_features.py          # Paper feature mixins
├── search_engine/                 # Index algorithms
├── storage_engine/                # Storage backends
│   ├── storage_factory.py
│   ├── memory_storage.py
│   ├── redis_storage.py
│   └── sagedb_storage.py
└── utils/                         # Utility functions
```

## Quick Start (Advanced)

```python
from sage.neuromem import UnifiedCollection
from sage.neuromem.memory_collection import TripleStorageMixin, LinkEvolutionMixin

# Create collection with paper features
class AdvancedCollection(UnifiedCollection, TripleStorageMixin, LinkEvolutionMixin):
    pass

collection = AdvancedCollection("my_advanced_collection")

# Use advanced features
collection.insert("id1", {"text": "information"})

# Store triple relationships
triple = collection.store_triple(
    query="What is X?",
    passage="X is...",
    answer="X"
)

# Track link evolution
collection.evolve_links("source_id", "target_id", metadata={"confidence": 0.9})
```

## Migration from v0.1.x

If you're upgrading from v0.1.x or earlier versions, see [MIGRATION_GUIDE.md](docs/dev-note/MIGRATION_GUIDE.md) for detailed migration instructions.

### Quick Migration Summary

```python
# Old (v0.1.x)
from sage.neuromem import VDBMemoryCollection
collection = VDBMemoryCollection({"name": "test"})

# New (v0.2.1+)
from sage.neuromem import UnifiedCollection
collection = UnifiedCollection("test", storage_backend="memory")
collection.add_index({"name": "default", "index_type": "faiss", "dim": 768})
```
    texts=["Hello world", "Goodbye world"],
    metadatas=[{"source": "doc1"}, {"source": "doc2"}]
)

# Create index
index_config = {
    "name": "my_index",
    "embedding_model": "mockembedder",
    "dim": 128,
    "backend_type": "FAISS"
}
collection.create_index(index_config)

# Retrieve
results = collection.retrieve(
    "Hello",
    index_name="my_index",
    topk=5
)
```

## Package Structure

NeuroMem is part of the SAGE ecosystem and installed as a namespace package:
- **Package name on PyPI**: `isage-neuromem`
- **Import path**: `sage.neuromem`
- **Namespace**: Part of SAGE (Structured AI Graph Engine)

## Documentation

- **[CollectionConfig Guide](docs/COLLECTION_CONFIG_GUIDE.md)** - Complete configuration management documentation
  - Creating collections from code, dict, and YAML
  - Index configuration and storage backend selection
  - Migration guide from earlier compatible formats
  - Best practices and examples

- **[Memory Services API Reference](docs/services/API_REFERENCE.md)** - Detailed API documentation for memory services
- **[Contributing Guide](docs/CONTRIBUTING.md)** - Development guidelines and contribution workflow

## Benchmarks

Comprehensive benchmark suite is available in `benchmarks/`:
- **Experiment Pipeline**: Complete benchmark pipeline for memory operations
- **Evaluation Tools**: Performance analysis and metrics
- **Configurations**: Pre-configured test scenarios

See [benchmarks/README.md](benchmarks/README.md) for details.

## Future Plans

This sub-project is designed as a core memory component of SAGE and may be rewritten in C++/Rust for better performance in the future.

## Part of SAGE Ecosystem

NeuroMem is a component of the SAGE (Structured AI Graph Engine) project by IntelliStream Team. -->

## License

Apache-2.0 License - see LICENSE file for details.
