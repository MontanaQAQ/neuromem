![NeuroMem Logo](docs/assets/neuromem.png)

<h3 align="center">
Love grows from the smallest of memories
</h3>

NeuroMem is a subproject of [SAGE](https://github.com/intellistream/SAGE), dedicated to exploring memory systems for large language models.

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
from sage.neuromem import MemoryManager

# Create memory manager
manager = MemoryManager()

# Create a collection
config = {
    "name": "my_collection",
    "backend_type": "VDB",
    "description": "My vector database collection"
}
collection = manager.create_collection(config)
```

For more examples, see [examples/](examples/).

## Features

- **Multiple Backend Support**: VDB (Vector Database), KV (Key-Value), Graph
- **Flexible Storage Engine**: Pluggable storage backends for vectors, text, and metadata
- **Powerful Search Engine**: Multiple index types (FAISS, BM25s, etc.)
- **Collection Management**: Create, load, store, and manage memory collections
- **Memory Manager**: Centralized management of multiple collections

## Architecture

```
sage/neuromem/
├── memory_manager.py          # Central manager for collections
├── memory_collection/         # Collection abstractions
│   ├── base_collection.py
│   ├── vdb_collection.py
│   ├── kv_collection.py
│   └── graph_collection.py
├── search_engine/             # Index implementations
│   ├── vdb_index/
│   ├── kv_index/
│   └── graph_index/
├── storage_engine/            # Storage backends
│   ├── vector_storage.py
│   ├── text_storage.py
│   └── metadata_storage.py
└── utils/                     # Utility functions
```

## Quick Start

```python
from sage.neuromem import MemoryManager

# Create manager
manager = MemoryManager()

# Create a VDB collection
config = {
    "name": "my_collection",
    "backend_type": "VDB",
    "description": "My vector database collection"
}
collection = manager.create_collection(config)

# Insert data
collection.batch_insert_data(
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
