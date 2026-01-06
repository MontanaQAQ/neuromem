# Contributing to NeuroMem

Thank you for your interest in contributing to NeuroMem! This guide will help you get started.

## 🚀 Quick Start

### Development Setup

```bash
# Install in development mode
./quickstart.sh --dev --yes

# Or manually
pip install -e . --no-deps
pip install isage-common isagevdb pytest pytest-cov pytest-mock
pre-commit install
```

### Running Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=neuromem --cov-report=html

# Run specific test file
pytest tests/unit/neuromem/indexes/test_bm25_index.py -v

# Run quick tests only (skip slow/gpu tests)
pytest tests/unit/ -m "not slow and not gpu"
```

### Code Quality

```bash
# Run pre-commit hooks
pre-commit run --all-files

# Format code with ruff
ruff format .

# Lint code with ruff
ruff check . --fix
```

## 📋 Development Workflow

### 1. Before You Start

- Fork the repository
- Clone your fork: `git clone https://github.com/YOUR_USERNAME/NeuroMem.git`
- Add upstream remote: `git remote add upstream https://github.com/intellistream/NeuroMem.git`
- Create a new branch: `git checkout -b feature/your-feature-name`

### 2. Making Changes

- Write clean, documented code following project conventions
- Add/update tests for new functionality
- Ensure all tests pass: `pytest tests/unit/ -v`
- Run code quality checks: `pre-commit run --all-files`

### 3. Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<body (optional)>

<footer (optional)>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build process or auxiliary tool changes
- `perf`: Performance improvements

**Examples:**
```bash
git commit -m "feat(memory): add hierarchical graph indexing"
git commit -m "fix(vdb): correct cosine distance calculation"
git commit -m "docs: update installation guide for Python 3.11"
git commit -m "test(indexes): add edge cases for BM25"
```

### 4. Submitting Pull Requests

- Push your changes: `git push origin feature/your-feature-name`
- Open a pull request on GitHub
- Ensure all CI checks pass
- Request review from maintainers
- Address review feedback

## 🏗️ Architecture Guidelines

NeuroMem follows a modular architecture:

```
neuromem/
├── memory_manager.py           # Central manager
├── memory_collection/          # Collection types
│   ├── indexes/               # Index implementations
│   └── base_collection.py
├── services/                   # Memory services
│   ├── partitional/           # Partition-based services
│   └── hierarchical/          # Hierarchy-based services
├── search_engine/             # Search algorithms
├── storage_engine/            # Storage backends
└── utils/                     # Utilities
```

### Key Principles

1. **Modular Design**: Each component should be independent and reusable
2. **Type Hints**: All functions must have proper type annotations
3. **Documentation**: Docstrings for all public APIs
4. **Testing**: Comprehensive unit tests for new features
5. **Error Handling**: Clear error messages with context

## 📝 Code Style

### Python Style

- Follow PEP 8
- Line length: 100 characters max
- Use type hints for all function signatures
- Docstrings in Google style format

**Example:**

```python
from typing import Optional, Dict, Any

def create_index(
    name: str,
    dim: int,
    backend_type: str = "FAISS",
    metadata: Optional[Dict[str, Any]] = None
) -> Index:
    """Create a new vector index.
    
    Args:
        name: Index name.
        dim: Vector dimension.
        backend_type: Backend type (FAISS, SageVDB).
        metadata: Optional metadata dict.
        
    Returns:
        Index: Created index instance.
        
    Raises:
        ValueError: If dim is invalid.
    """
    # Implementation
```

### Import Organization

```python
# Standard library
import os
from typing import List, Dict

# Third-party
import numpy as np
import yaml

# Local imports
from neuromem.memory_collection import BaseCollection
from neuromem.services import BaseService
```

## 🐛 Reporting Issues

### Bug Reports

Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, dependencies)
- Minimal code example

### Feature Requests

Include:
- Clear use case description
- Proposed solution (if any)
- Benefits and potential drawbacks
- Related issues or PRs

## 📚 Documentation

- Update README.md for user-facing changes
- Update .github/copilot-instructions.md for architectural changes
- Add docstrings for all new functions/classes
- Update type hints when signatures change

## 🔍 Testing Guidelines

### Unit Tests

- Test one component at a time
- Use mocks for external dependencies
- Cover edge cases and error conditions
- Keep tests fast (< 1s per test)

### Test Structure

```python
import pytest
from neuromem.memory_collection.indexes import BM25Index

class TestBM25Index:
    """Test BM25Index functionality."""
    
    def test_create_index(self):
        """Test index creation."""
        index = BM25Index(name="test")
        assert index.name == "test"
    
    def test_query_empty_index(self):
        """Test querying empty index."""
        index = BM25Index(name="test")
        results = index.query("test query")
        assert len(results) == 0
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.slow
def test_large_dataset():
    """Test with large dataset (slow)."""
    pass

@pytest.mark.gpu
def test_gpu_acceleration():
    """Test GPU functionality (requires GPU)."""
    pass
```

## 🔗 Dependencies

- **Core**: isage-common, isagevdb, numpy, pyyaml
- **Testing**: pytest, pytest-cov, pytest-mock
- **Development**: pre-commit, ruff

When adding dependencies:
- Update `pyproject.toml`
- Justify why the dependency is needed
- Consider maintenance burden

## 📞 Contact

- GitHub Issues: https://github.com/intellistream/NeuroMem/issues
- Email: shuhao_zhang@hust.edu.cn

## 📄 License

By contributing, you agree that your contributions will be licensed under the project's license.
