# NeuroMem Copilot Instructions

## Project Overview

**NeuroMem** is a standalone memory management engine for RAG (Retrieval-Augmented Generation) applications. It provides flexible memory collection abstractions with multi-backend support (Vector DB, Key-Value, Graph).

### Core Architecture

**v0.2.1+ Architecture** (UnifiedCollection Era):

```
neuromem/
├── memory_manager.py                    # Central lifecycle manager
├── memory_collection/
│   ├── unified_collection.py            # ⭐ Unified abstraction (primary)
│   ├── collection_config.py             # YAML configuration management
│   ├── indexes/                         # Index implementations
│   │   ├── faiss_index.py              # Vector search
│   │   ├── bm25_index.py               # Text search
│   │   ├── graph_index.py              # Graph operations
│   │   └── ...other indexes
│   └── paper_features.py                # Advanced memory mixins
├── search_engine/                       # Index algorithms (FAISS, BM25, etc.)
├── storage_engine/
│   ├── storage_factory.py               # Storage backend factory
│   ├── memory_storage.py                # In-memory backend
│   ├── redis_storage.py                 # Redis backend
│   └── sagedb_storage.py                # Vector DB backend
├── services/                            # High-level services (hierarchical, partitional, graph)
└── utils/                               # Utilities

### Key Design Patterns

1. **Unified Collection Pattern**: `UnifiedCollection` as primary abstraction for all memory types
2. **Mixin Pattern**: Paper features implemented as mixins (TripleStorageMixin, LinkEvolutionMixin, etc.)
3. **Service Registry Pattern**: All memory services registered through `MemoryServiceRegistry`
4. **Factory Pattern**: `IndexFactory` for creating various index types, `StorageFactory` for storage backends
5. **Plugin Storage**: Pluggable storage backends (Memory, Redis, SageDB)
6. **Configuration-First**: YAML-based configuration management via `CollectionConfig`
7. **Lazy Loading**: Collections loaded on-demand from disk

### Version History

- **v0.2.1.0** (Current): UnifiedCollection production-ready
  - Single abstraction for all memory types
  - Pluggable storage backends
  - Simplified codebase (removed 6 old Collection classes)
  - All 354 unit tests passing

- **v0.2.0.0**: Initial stable release with individual Collection types
- **v0.1.x**: Early development phase

---

## Code Style & Conventions

### Python Standards

- **Python Version**: 3.10+
- **Type Hints**: Always use type annotations (from `__future__ import annotations`)
- **Docstrings**:
  - Use Chinese for internal modules (memory_manager.py, services)
  - Use English for public APIs and examples
  - Include typical usage examples for complex classes

### Naming Conventions

- **Classes**: PascalCase (e.g., `MemoryManager`, `UnifiedCollection`)
- **Functions/Methods**: snake_case (e.g., `create_collection`, `batch_insert_data`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TOP_K`)
- **Private Members**: prefix with `_` (e.g., `_load_from_disk`)

### Import Organization

```python
# 1. Future imports
from __future__ import annotations

# 2. Standard library
import json
from pathlib import Path
from typing import Any

# 3. Third-party (SAGE dependencies)
from sage.common.utils.logging.custom_logger import CustomLogger
from sagedb import SageDB

# 4. Local imports (relative)
from .memory_collection import UnifiedCollection
from .utils.path_utils import get_default_data_dir
```

### Error Handling

- Use specific exception types
- Log errors with `CustomLogger` from `sage.common`
- Provide meaningful error messages with context
- Return `False` or `None` for soft failures, raise for critical errors

---

## Core Components Guide

### 1. MemoryManager

Central lifecycle manager for UnifiedCollection instances.

**Key Methods**:
- `create_collection(name, **config)`: Create new collection
- `get_collection(name)`: Get or lazy-load collection
- `persist(name)`: Save collection to disk
- `delete_collection(name)`: Remove collection

**Usage Pattern**:
```python
manager = MemoryManager()
collection = manager.create_collection("my_data")
collection.insert("id1", {"text": "hello"})
manager.persist("my_data")
```

### 2. UnifiedCollection

Unified abstraction for all memory types. Supports multiple backends and indexes.

**Key Methods**:
- `insert(data_id, data)`: Insert single item
- `batch_insert(batch_data)`: Bulk insert
- `retrieve(query, top_k, index_name)`: Search
- `create_index(index_config)`: Add index
- `to_dict()` / `from_dict(data)`: Serialization

**Index Types**: FAISS, BM25s, LSH, FIFO, Segment, Graph

### 3. Services Layer

High-level abstractions built on UnifiedCollection.

**Service Categories**:
- **Hierarchical**: `tree_node`, `tree_index`, `segment`, `summarization`
- **Partitional**: `fifo_queue`, `lsh_hash`, `keyword_partition`
- **Graph**: `linknote_graph`, `property_graph`, `inverted_index`

**Service Creation**:
```python
from neuromem.services import MemoryServiceRegistry

service = MemoryServiceRegistry.create(
    service_type="fifo_queue",
    collection=collection,
    config={"max_size": 100}
)
```

### 4. Storage Engine

Pluggable storage backends for different data types.

**Storage Types**:
- `VectorStorage`: FAISS, SageDB, Mock
- `TextStorage`: In-memory, Redis
- `MetadataStorage`: JSON, SQLite (planned)

---

## Development Guidelines

### When Adding New Features

1. **New Index Type**:
   - Inherit from `BaseIndex` in `memory_collection/indexes/`
   - Implement `build()`, `search()`, `to_dict()`, `from_dict()`
   - Register in `IndexFactory`

2. **New Service**:
   - Inherit from `BaseMemoryService` in `services/base_service.py`
   - Implement `insert()`, `retrieve()`, `delete()`
   - Register via `@MemoryServiceRegistry.register("service_name")`

3. **New Storage Backend**:
   - Implement storage interface in `storage_engine/`
   - Add to factory method in respective storage module

### Testing Approach

- **Unit Tests**: `tests/unit/` - Component-level testing
- **Integration Tests**: `tests/integration/` - Multi-component workflows
- **E2E Tests**: `tests/e2e/` - Complete user scenarios
- **Performance Tests**: `tests/performance/` - Benchmarks

Run tests:
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/test_complete_workflows.py
```

### Configuration Files

YAML configs in `neuromem/config/` define feature combinations:
- `feature_*.yaml`: Pre-configured feature sets
- `*_inverted.yaml`: Inverted index variants
- `semantic_*.yaml`: Semantic search configs

**Config Structure**:
```yaml
collection_name: "my_collection"
indexes:
  - name: "my_index"
    backend_type: "FAISS"
    embedding_model: "openai"
    dim: 1536
```

---

## Dependencies & Integration

### SAGE Ecosystem

NeuroMem is part of the SAGE project and uses:
- `isage-common`: Logging, embeddings, utilities
- `isage-vdb`: SageDB vector database backend

### Optional Dependencies

- **redis**: For Redis KV storage backend
- **neo4j**: For Neo4j graph backend
- **networkx**: For in-memory graph operations

---

## Common Patterns & Anti-Patterns

### ✅ DO

- Use `UnifiedCollection` as the primary abstraction
- Create indexes via `create_index()` method, not directly
- Persist collections after batch operations: `manager.persist(name)`
- Use service registry for high-level features
- Add type hints and docstrings
- Log important operations with `self.logger`

### ❌ DON'T

- Don't bypass `MemoryManager` for collection creation
- Don't create index instances directly - use `IndexFactory`
- Don't hardcode paths - use `path_utils.get_default_data_dir()`
- Don't mix English/Chinese in same module (be consistent)
- Don't commit commented-out debug code
- Don't use `print()` - use `CustomLogger` instead

---

## File Organization

### When Creating New Files

- **Indexes**: `neuromem/memory_collection/indexes/`
- **Services**: `neuromem/services/hierarchical/` or `services/partitional/`
- **Storage**: `neuromem/storage_engine/`
- **Utilities**: `neuromem/utils/`
- **Tests**: Mirror structure in `tests/unit/neuromem/`
- **Examples**: `examples/`

### Module Structure Template

```python
"""Module description (Chinese for internal, English for public)

职责/Responsibilities:
- Key responsibility 1
- Key responsibility 2

典型用法/Typical Usage:
    >>> from neuromem import ...
    >>> instance = ...
"""

from __future__ import annotations

# imports...

class MyClass:
    """Brief description

    Detailed explanation...

    Attributes:
        attr1: Description
        attr2: Description
    """

    def __init__(self, ...):
        """Initialize...

        Args:
            param1: Description
            param2: Description
        """
        pass
```

---

## Special Considerations

### Future Roadmap

- Potential rewrite in C++/Rust for performance
- May be separated into standalone repository
- Keep APIs stable and well-documented

### Performance

- Use batch operations when possible
- Lazy-load collections to reduce memory footprint
- Consider index type trade-offs (FAISS for large-scale, BM25s for text)

### Compatibility

- Python 3.10+ required
- NumPy < 2.3.0 (compatibility constraint)
- Test with multiple vector backends (FAISS, SageDB, Mock)

---

## Publishing to PyPI

### Using sage-pypi-publisher

NeuroMem uses `sage-pypi-publisher` for building and publishing to PyPI. This tool automatically compiles Python source to bytecode for better performance and IP protection.

**Installation**:
```bash
pip install --upgrade sage-pypi-publisher
```

**Publishing Workflow**:

1. **Update Version** (use 4-digit semantic versioning):
   ```bash
   # Update these files:
   # - pyproject.toml: version = "0.2.0.1"
   # - sage/neuromem/_version.py: __version__ = "0.2.0.1"
   ```

2. **Commit Version Changes**:
   ```bash
   git add pyproject.toml sage/neuromem/_version.py
   git commit -m "chore: bump version to X.X.X.X"
   git push origin main-dev
   ```

3. **Build and Upload** (one command):
   ```bash
   cd /path/to/neuromem
   sage-pypi-publisher build . -o /tmp/neuromem-build -u -r pypi --no-dry-run
   ```

**What sage-pypi-publisher Does**:
- ✅ Auto-detects pure Python package
- ✅ Compiles `.py` → `.pyc` (keeps `__init__.py` and `_version.py`)
- ✅ Builds optimized wheel (bytecode compilation)
- ✅ Validates package with `twine check`
- ✅ Uploads to PyPI with proper authentication
- ✅ Provides package URL for verification

**Publishing Options**:
- **Test PyPI**: `-r testpypi` (for testing before production)
- **Dry Run**: `--dry-run` (default, simulates upload without actually uploading)
- **Production**: `--no-dry-run` (required for actual upload)

**Verification**:
```bash
# Check uploaded version
pip index versions isage-neuromem

# Install from PyPI
pip install isage-neuromem==X.X.X.X
```

**Benefits of Bytecode Compilation**:
- Faster loading times (pre-compiled)
- Reduced package inspection
- Similar wheel size to source distribution
- Maintains full functionality

---

## Additional Resources

- **API Reference**: `neuromem/services/API_REFERENCE.md`
- **Benchmarks**: `neuromem/services/BENCHMARKS.md`
- **Contributing**: `CONTRIBUTING.md`
- **Examples**: `examples/` directory
- **CI/CD Guide**: `docs/CI_CD_README.md`

---

## When Helping with This Project

1. **Understand context**: Check which layer you're working in (manager/collection/service/storage)
2. **Follow patterns**: Use existing code as reference (especially `memory_manager.py`)
3. **Test thoroughly**: Run relevant test suite before suggesting changes
4. **Document clearly**: Match existing doc style (Chinese/English per module)
5. **Preserve architecture**: Don't break abstractions or bypass layers
6. **Version updates**: Always use 4-digit semantic versioning (X.X.X.X)
7. **Publishing**: Use `sage-pypi-publisher` for all PyPI releases

## Polyrepo coordination (mandatory)

- This repository is an independent SAGE sub-repository and is developed/released independently.
- Do not assume sibling source directories exist locally in `intellistream/SAGE`.
- For cross-repo rollout, publish this repo/package first, then bump the version pin in `SAGE/packages/sage/pyproject.toml` when applicable.
- Do not add local editable installs of other SAGE sub-packages in setup scripts or docs.
