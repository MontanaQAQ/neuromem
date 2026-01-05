# isage-neuromem

**NeuroMem** is a brain-inspired memory management engine for SAGE (Structured AI Graph Engine). It provides flexible memory collection abstractions with support for vector databases, key-value stores, and graph structures, designed specifically for RAG (Retrieval-Augmented Generation) applications.

## Installation

```bash
pip install isage-neuromem
```

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

## Future Plans

This sub-project is designed as a core memory component of SAGE and may be rewritten in C++/Rust for better performance in the future.

## License

Apache-2.0 License - see LICENSE file for details.

## Part of SAGE Ecosystem

NeuroMem is a component of the SAGE (Structured AI Graph Engine) project by IntelliStream Team.
