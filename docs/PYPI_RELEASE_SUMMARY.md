# PyPI Release Summary: isage-data v0.1.1

**Date**: January 5, 2026  
**Package**: `isage-data`  
**Version**: 0.1.1  
**PyPI Link**: https://pypi.org/project/isage-data/0.1.1/

---

## 🎯 Overview

Successfully published `isage-data` v0.1.1 to PyPI, providing unified data loaders for memory benchmark datasets. This package is now a dependency for NeuroMem's benchmark suite.

---

## 📦 Package Details

### Package Information
- **Name**: `isage-data`
- **Namespace**: `sage.data`
- **Repository**: https://github.com/intellistream/sageData
- **License**: MIT
- **Python**: >= 3.10

### Included Data Loaders
- ✅ **LongMemEval** - Long-context memory evaluation benchmark (NEW in v0.1.1)
- ✅ **Locomo** - Long-context modeling dataset
- ✅ **MemAgentBench** - Conflict resolution scenarios
- ✅ **BBH** - BIG-Bench Hard reasoning tasks
- ✅ **MMLU** - Massive Multitask Language Understanding
- ✅ **GPQA** - Graduate-Level Question Answering
- ✅ **QA Base** - Question-Answering with knowledge base
- ✅ **Agent Benchmark** - Agent task planning and execution
- ✅ **Agent SFT** - Agent supervised fine-tuning data
- ✅ **Agent Tools** - Tool catalog for agents
- ✅ **Control Plane Benchmark** - Workload benchmarking

---

## 🔄 Migration Process

### sageData Repository Changes (main-dev branch)

**1. Directory Restructuring**
```bash
# Before
sageData/
├── sources/
│   ├── locomo/
│   ├── memagentbench/
│   └── ...
├── __init__.py
└── manager.py

# After
sageData/
├── sage/
│   ├── __init__.py  # Namespace marker
│   └── data/
│       ├── __init__.py
│       ├── manager.py
│       └── sources/
│           ├── longmemeval/  # NEW
│           ├── locomo/
│           ├── memagentbench/
│           └── ...
├── pyproject.toml  # NEW
└── LICENSE  # NEW (MIT)
```

**2. Key Files Added**
- `sage/__init__.py` - Namespace package marker with `pkgutil.extend_path`
- `pyproject.toml` - Package configuration for PyPI
- `LICENSE` - MIT License
- `sage/data/sources/longmemeval/` - LongMemEval data loader (from feat/align-longmemeval)

**3. Git Operations**
- Used `git mv` to preserve file history (102 files)
- Added longmemeval from `origin/feat/align-longmemeval` branch
- Committed to main-dev branch directly
- Pushed to GitHub: https://github.com/intellistream/sageData/commit/5d714a3

---

## 📝 Configuration Files

### pyproject.toml
```toml
[project]
name = "isage-data"
version = "0.1.1"
dependencies = [
    "isage-common>=0.2.0",
    "pandas>=2.0.0",
    "numpy>=1.26.0,<2.3.0",
    "pyyaml>=6.0",
    "datasets>=2.14.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["sage.data*"]
namespaces = true
```

### LICENSE
```
MIT License
Copyright (c) 2024-2026 IntelliStream Team
```

---

## 🚀 Publishing Process

### Tools Used
- **sage-pypi-publisher** v0.1.5
- Bytecode compilation enabled
- Uploaded to PyPI with `--no-dry-run`

### Build Statistics
- Python files compiled: 64
- .pyc files generated: 52
- Wheel size: 1.6 MB
- Total package files: 97

### Commands Executed
```bash
cd /home/shuhao/sageData
git checkout main-dev
git checkout origin/feat/align-longmemeval -- sources/longmemeval
git mv sources sage/data/
git mv __init__.py sage/data/
git mv manager.py sage/data/
# Create sage/__init__.py, pyproject.toml, LICENSE
git commit -m "refactor: Migrate to sage.data namespace for PyPI (v0.1.1)"
git push origin main-dev

sage-pypi-publisher build . -o /tmp/sagedata-v0.1.1 -u -r pypi --no-dry-run
```

---

## 🔗 NeuroMem Integration

### neuromem Repository Changes (main-dev branch)

**1. Added benchmark Optional Dependencies**

In `neuromem/pyproject.toml`:
```toml
[project.optional-dependencies]
benchmark = [
    "isage-data>=0.1.0",
    "pytest-benchmark>=4.0.0",
    "pandas>=2.0.0",
    "matplotlib>=3.7.0",
]
```

**2. Created Missing __init__.py Files**

Added 18 `__init__.py` files in:
- `benchmarks/experiment/config/` (7 subdirectories)
- `benchmarks/experiment/script/` (6 subdirectories)
- `benchmarks/experiment/libs/`
- `benchmarks/experiment/tools/`
- `benchmarks/experiment/mem_docs/`

**3. Updated Documentation**

Created/Updated:
- `benchmarks/README.md` - Added installation instructions with isage-data
- `docs/SAGEDATA_SETUP.md` - Complete guide for sageData PyPI setup
- `docs/PYPI_RELEASE_SUMMARY.md` - This file

**4. Git Operations**
- Committed to main-dev branch
- Pushed to GitHub: https://github.com/intellistream/neuromem/commit/51f09cb

---

## ✅ Verification Results

### Installation Test
```bash
pip install --upgrade isage-data
# Successfully installed isage-data-0.1.1
```

### Import Tests
```python
✅ from sage.neuromem import MemoryManager
✅ import benchmarks
✅ from sage.data.sources.longmemeval import LongMemEvalDataLoader
✅ from sage.data.sources.locomo import LocomoDataLoader
✅ from sage.data.sources.memagentbench.conflict_resolution_loader import ConflictResolutionDataLoader
✅ from benchmarks.experiment.libs.memory_source import MemorySource
```

All imports successful! 🎉

---

## 📚 User Installation

### Basic Installation
```bash
pip install isage-neuromem
```

### With Benchmark Support
```bash
pip install isage-neuromem[benchmark]
```

This will automatically install:
- `isage-data>=0.1.0` (includes LongMemEval, Locomo, MemAgentBench, etc.)
- `pytest-benchmark>=4.0.0`
- `pandas>=2.0.0`
- `matplotlib>=3.7.0`

### Development Installation
```bash
# Clone both repositories
git clone https://github.com/intellistream/neuromem.git
git clone https://github.com/intellistream/sageData.git

# Install in development mode
cd sageData && pip install -e .
cd ../neuromem && pip install -e .[dev,benchmark]
```

---

## 🔍 Dependency Graph

```
isage-neuromem (neuromem repo)
├── isage-common  ✅ (PyPI)
├── isagedb       ✅ (PyPI)
└── [benchmark]
    └── isage-data ✅ (PyPI, v0.1.1)
        ├── isage-common
        ├── pandas
        ├── numpy
        ├── pyyaml
        └── datasets (Hugging Face)
```

---

## 📈 Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-05 | Initial release (missing longmemeval) |
| 0.1.1 | 2026-01-05 | Added longmemeval data loader |

---

## 🎓 Lessons Learned

1. **Namespace Packages**: Use `pkgutil.extend_path` in `sage/__init__.py` for proper namespace package support
2. **Git History Preservation**: Always use `git mv` instead of manual copy-paste to preserve file history
3. **Branch Strategy**: Can publish directly from main-dev without creating release branches
4. **Testing PyPI First**: Always test on TestPyPI before publishing to production PyPI
5. **sage-pypi-publisher**: Excellent tool for automated bytecode compilation and publishing
6. **Optional Dependencies**: Use `[project.optional-dependencies]` for benchmark-specific packages

---

## 🔗 Links

- **isage-data PyPI**: https://pypi.org/project/isage-data/
- **sageData GitHub**: https://github.com/intellistream/sageData
- **neuromem GitHub**: https://github.com/intellistream/neuromem
- **sage-pypi-publisher**: https://github.com/intellistream/sage-pypi-publisher

---

## 📞 Contact

- **Team**: IntelliStream
- **Email**: shuhao_zhang@hust.edu.cn
- **Repository**: https://github.com/intellistream

---

**Status**: ✅ Complete and Verified  
**Published**: January 5, 2026  
**Next Steps**: Monitor PyPI downloads, gather user feedback, prepare v0.2.0 with additional datasets
