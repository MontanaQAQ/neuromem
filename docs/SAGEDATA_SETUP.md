# sageData PyPI 发布指南

## 📦 概述

`sageData` 是 SAGE 生态系统的数据加载模块，提供统一接口加载 LongMemEval、Locomo、MemAgentBench 等数据集。
NeuroMem 的 benchmark 套件依赖此包。

**GitHub 仓库**: https://github.com/intellistream/sageData  
**PyPI 包名**: `isage-data` (计划中)  
**命名空间**: `sage.data`

---

## 🎯 发布到 PyPI 的步骤

### 1. 在 sageData 仓库创建 `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "isage-data"
version = "0.1.0"
description = "SAGE Data - Unified data loaders for memory benchmark datasets"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Apache-2.0"}
authors = [
    {name = "IntelliStream Team", email = "shuhao_zhang@hust.edu.cn"}
]
keywords = ["dataset", "benchmark", "memory", "ai", "longmemeval", "locomo"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

dependencies = [
    "isage-common>=0.2.0",  # For BatchFunction and core utilities
    "pandas>=2.0.0",
    "numpy>=1.26.0,<2.3.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[project.urls]
Homepage = "https://github.com/intellistream/sageData"
Repository = "https://github.com/intellistream/sageData"
Documentation = "https://github.com/intellistream/sageData/blob/main/README.md"

[tool.setuptools]
zip-safe = false

[tool.setuptools.packages.find]
where = ["."]
include = ["sage.data*"]
namespaces = true
```

### 2. 创建 `sage/__init__.py` (命名空间包)

```python
"""SAGE ecosystem root namespace package."""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
```

### 3. 确保目录结构

```
sageData/
├── sage/
│   ├── __init__.py          # 命名空间标记
│   └── data/
│       ├── __init__.py
│       └── sources/
│           ├── __init__.py
│           ├── longmemeval/
│           ├── locomo/
│           └── memagentbench/
├── pyproject.toml
├── README.md
└── LICENSE
```

### 4. 构建和发布

```bash
# 在 sageData 仓库根目录
pip install build twine

# 构建分发包
python -m build

# 发布到 TestPyPI (测试)
python -m twine upload --repository testpypi dist/*

# 发布到正式 PyPI
python -m twine upload dist/*
```

---

## 🔧 NeuroMem 集成方式

### 用户安装

**基础安装** (不含 benchmark):
```bash
pip install isage-neuromem
```

**完整安装** (含 benchmark 依赖):
```bash
pip install isage-neuromem[benchmark]
```

**全功能安装** (所有后端 + benchmark):
```bash
pip install isage-neuromem[full,benchmark]
```

### 开发者安装

```bash
# 克隆两个仓库
git clone https://github.com/intellistream/neuromem.git
git clone https://github.com/intellistream/sageData.git

# 以开发模式安装
cd sageData && pip install -e .
cd ../neuromem && pip install -e .[dev,benchmark]
```

---

## 📝 依赖关系图

```
isage-neuromem (neuromem 仓库)
├── isage-common  (已在 PyPI)
├── isage-vdb       (已在 PyPI)
└── [benchmark] → isage-data  (需要发布)
                  └── isage-common
```

---

## ✅ 验证清单

在 sageData 仓库发布前：

- [ ] 确认 `sage/__init__.py` 使用 `pkgutil.extend_path`
- [ ] 确认所有 `__init__.py` 文件存在
- [ ] 测试本地安装: `pip install -e .`
- [ ] 测试导入: `from sage.data.sources.longmemeval import LongMemEvalDataLoader`
- [ ] 运行单元测试
- [ ] 更新 README.md 包含安装和使用示例
- [ ] 添加 LICENSE 文件
- [ ] 创建 Git tag: `v0.1.0`

在 neuromem 仓库：

- [ ] 更新 `pyproject.toml` 添加 `[project.optional-dependencies] benchmark`
- [ ] 创建 `__init__.py` 文件给所有 benchmarks 子目录
- [ ] 更新 `benchmarks/README.md` 说明依赖要求
- [ ] 测试安装: `pip install -e .[benchmark]`
- [ ] 运行 benchmark 验证脚本

---

## 🚀 发布后的使用

### Python 代码中

```python
# 用户代码 - 只需安装 isage-neuromem[benchmark]
from sage.neuromem import MemoryManager
from sage.data.sources.longmemeval import LongMemEvalDataLoader

# benchmarks 代码 - 直接导入
from benchmarks.experiment.libs.memory_source import MemorySource
```

### 文档更新

在 neuromem README.md 中添加：

```markdown
## 🧪 Running Benchmarks

To run the benchmark suite, install with benchmark dependencies:

\`\`\`bash
pip install isage-neuromem[benchmark]
\`\`\`

This will install `isage-data` which provides data loaders for:
- LongMemEval
- Locomo
- MemAgentBench

See [benchmarks/README.md](benchmarks/README.md) for details.
```

---

## 🔄 版本管理策略

### 独立版本号

- `isage-neuromem`: 专注于内存管理核心功能
- `isage-data`: 专注于数据加载和数据集接口

### 兼容性声明

在 neuromem 的 `pyproject.toml` 中使用宽松的版本约束：

```toml
benchmark = [
    "isage-data>=0.1.0,<1.0.0",  # 允许小版本更新
]
```

---

## 📞 需要帮助？

如果 sageData 发布过程中遇到问题：

1. 参考 neuromem 的 PyPI 发布流程 (已成功发布)
2. 查看 Python 打包官方文档: https://packaging.python.org/
3. 联系 SAGE 团队: shuhao_zhang@hust.edu.cn
