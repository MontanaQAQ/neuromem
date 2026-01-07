# NeuroMem 命名空间包迁移指南

## 概述

本指南详细说明如何将 NeuroMem 从独立包 (`neuromem.*`) 重构为 SAGE 命名空间包。为了兼顾 SAGE 归属、对外发布简洁度与内部兼容性，推荐：

- **对外发布/用户文档**：使用简短路径 **`from sage.neuromem import ...`**（发布包名仍为 `isage-neuromem`，命名空间前缀为 `sage.neuromem`）。
- **SAGE 内部现有代码**：沿用深层路径 `from sage.middleware.components.sage_mem.neuromem import ...`，通过适配器重导出 `sage.neuromem` 以保持兼容。

> 说明：轻量适配方式不需要移动代码目录，只需在 SAGE 侧提供命名空间适配器（`sage/neuromem/__init__.py`）重新导出 `neuromem`，并在 `sage/middleware/components/sage_mem/neuromem/__init__.py` 中再导出一次以满足内部路径。完整迁移步骤依然保留于下方，供需要时参考。

### 推荐导入策略（简化方案 C）

- **对外/文档首选**：`from sage.neuromem import MemoryManager`
- **兼容导入**：`from neuromem import MemoryManager`（保持对外独立包易用性）
- **SAGE 内部现有代码**：`from sage.middleware.components.sage_mem.neuromem import MemoryManager`（通过适配器二次导出）

> 说明：轻量适配方式不需要移动代码目录，只需在 SAGE 侧提供命名空间适配器（`sage/neuromem/__init__.py`）重新导出 `neuromem`，并在 `sage/middleware/components/sage_mem/neuromem/__init__.py` 中从 `sage.neuromem` 继续导出，以兼容内部深层路径。完整迁移步骤依然保留于下方，供需要时参考。

## 为什么要迁移？

**当前问题**：
- NeuroMem 独立包名为 `neuromem.*`
- SAGE 代码使用 `from sage.middleware.components.sage_mem.neuromem import ...`
- 两者不兼容，导致导入失败

**迁移后**：
- NeuroMem 安装到 `sage.middleware.components.sage_mem.neuromem` 命名空间
- SAGE 代码无需修改，直接可用
- 支持命名空间包特性，未来可扩展

## 快速开始

### 选项 1: 使用自动化脚本（推荐）

```bash
cd ~/neuromem
./neuromem_refactor.sh
```

### 选项 2: 手动执行

按照下面的详细步骤手动执行。

### 选项 3: 轻量适配（不移动目录，推荐给现阶段）

> 适用场景：对外发布主推 `from sage.neuromem import ...`，同时兼容内部深层路径 `from sage.middleware.components.sage_mem.neuromem import ...`，且暂不移动现有代码目录。

1. 创建命名空间目录与标记文件（两级 + 深层适配）：

```bash
mkdir -p sage
cat > sage/__init__.py << 'EOF'
"""SAGE namespace package (light adapter for neuromem)"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
EOF

mkdir -p sage/neuromem
cat > sage/neuromem/__init__.py << 'EOF'
"""Lightweight adapter: expose neuromem under sage.neuromem"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

try:
    from neuromem import *  # noqa: F401,F403
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "NeuroMem not installed. Please 'pip install isage-neuromem'"
    ) from exc
EOF

# 为兼容内部深层路径再导出一次
mkdir -p sage/middleware/components/sage_mem/neuromem
cat > sage/middleware/components/sage_mem/__init__.py << 'EOF'
"""SAGE-Mem namespace package (adapter layer)"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
EOF

cat > sage/middleware/components/sage_mem/neuromem/__init__.py << 'EOF'
"""Adapter: reuse sage.neuromem for deep path compatibility"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

try:
    from sage.neuromem import *  # noqa: F401,F403
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "NeuroMem not installed under sage.neuromem. Please 'pip install isage-neuromem'"
    ) from exc
EOF
```

2. 验证导入：

```bash
python3 - << 'EOF'
from sage.neuromem import MemoryManager
print("✅ sage.neuromem usable", MemoryManager)
EOF
```

> 如需与 SAGE 主仓库的深层目录 (`sage.middleware.components.sage_mem.neuromem`) 完全一致，请继续阅读下方完整迁移步骤。

## 详细迁移步骤

### 步骤 1: 备份

```bash
cd ~/neuromem
cp -r neuromem neuromem_backup
```

### 步骤 2: 创建命名空间目录结构

```bash
mkdir -p sage/middleware/components/sage_mem
```

### 步骤 3: 移动代码（保留 Git 历史）

```bash
# 如果是 git 仓库（推荐）
git mv neuromem sage/middleware/components/sage_mem/

# 或者普通移动
mv neuromem sage/middleware/components/sage_mem/
```

### 步骤 4: 创建命名空间标记文件

```bash
# sage/__init__.py
cat > sage/__init__.py << 'EOF'
"""SAGE namespace package"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
EOF

# sage/middleware/__init__.py
cat > sage/middleware/__init__.py << 'EOF'
"""SAGE middleware namespace package"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
EOF

# sage/middleware/components/__init__.py
cat > sage/middleware/components/__init__.py << 'EOF'
"""SAGE middleware components namespace package"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
EOF

# sage/middleware/components/sage_mem/__init__.py
cat > sage/middleware/components/sage_mem/__init__.py << 'EOF'
"""SAGE-Mem namespace package for memory management implementations"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
EOF
```

### 步骤 5: 更新 pyproject.toml

修改 `pyproject.toml`:

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["sage.middleware.components.sage_mem.neuromem*"]  # 修改这行
exclude = ["tests*", "examples*"]

[tool.setuptools]
zip-safe = false  # 添加这行
```

### 步骤 6: 验证 pyproject.toml 配置

检查 `pyproject.toml`:

```python
setup(
    name="isage-neuromem",
    version="0.2.0",  # 升级版本号
    packages=find_packages(
        where=".",
        include=["sage.middleware.components.sage_mem.neuromem*"],
        exclude=["tests*", "examples*"]
    ),
    # ... 其他配置 ...
)
```

### 步骤 7: 验证包结构

```bash
python3 << 'EOF'
from setuptools import find_packages

packages = find_packages(
    where=".",
    include=["sage.middleware.components.sage_mem.neuromem*"],
    exclude=["tests*", "examples*"]
)

print("找到的包:")
for pkg in sorted(packages):
    print(f"  - {pkg}")
EOF
```

应该输出：
```
找到的包:
  - sage.middleware.components.sage_mem.neuromem
  - sage.middleware.components.sage_mem.neuromem.config
  - sage.middleware.components.sage_mem.neuromem.memory_collection
  - sage.middleware.components.sage_mem.neuromem.search_engine
  - ...
```

### 步骤 8: 更新内部导入（重要！）

**NeuroMem 包内部的相对导入不需要改**，但需要更新以下文件：

#### 8.1 更新 `sage/middleware/components/sage_mem/neuromem/__init__.py`

```python
"""
NeuroMem - Brain-inspired memory system for SAGE

This package is installed as part of the SAGE namespace.
Import path: sage.middleware.components.sage_mem.neuromem
"""

from ._version import __author__, __email__, __version__

from .memory_collection import (
    BaseMemoryCollection,
    GraphMemoryCollection,
    KVMemoryCollection,
    VDBMemoryCollection,
)
from .memory_manager import MemoryManager

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "MemoryManager",
    "BaseMemoryCollection",
    "VDBMemoryCollection",
    "KVMemoryCollection",
    "GraphMemoryCollection",
]
```

#### 8.2 更新 examples/

将所有 `examples/*.py` 中的导入从：
```python
from neuromem import MemoryManager
```

改为：
```python
from sage.middleware.components.sage_mem.neuromem import MemoryManager
```

#### 8.3 更新 tests/

将所有 `tests/**/*.py` 中的导入从：
```python
from neuromem.memory_manager import MemoryManager
```

改为：
```python
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
```

### 步骤 9: 更新文档

#### 9.1 更新 README.md

```markdown
# isage-neuromem

**NeuroMem** - Brain-inspired memory system for SAGE

## Installation

```bash
pip install isage-neuromem
```

## Usage

```python
# 推荐：通过 SAGE 命名空间导入
from sage.middleware.components.sage_mem.neuromem import MemoryManager

# 或者使用 SAGE 的便捷导入（如果 sage-middleware 已安装）
from sage.middleware.components.sage_mem import MemoryManager

# 创建 memory manager
manager = MemoryManager()
```

## Package Structure

NeuroMem is installed as part of the SAGE namespace:
- **Package name**: `isage-neuromem`
- **Import path**: `sage.middleware.components.sage_mem.neuromem`
- **Namespace**: Part of SAGE ecosystem
```

### 步骤 10: 构建和测试

```bash
# 清理旧的构建产物
rm -rf build/ dist/ *.egg-info/

# 构建包
python3 -m build

# 检查构建产物
tar -tzf dist/isage-neuromem-*.tar.gz | grep "sage/middleware" | head -10

# 测试安装
pip uninstall -y isage-neuromem  # 卸载旧版本
pip install -e .

# 验证导入
python3 << 'EOF'
from sage.middleware.components.sage_mem.neuromem import MemoryManager
print(f"✅ MemoryManager: {MemoryManager}")
EOF
```

### 步骤 11: 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 如果测试失败，检查导入路径是否都更新了
```

### 步骤 12: 提交更改

```bash
git add sage/
git add pyproject.toml
git add examples/ tests/ README.md
git rm -r neuromem  # 如果使用了 git mv，这步可跳过
git commit -m "refactor: convert to SAGE namespace package

- Move neuromem to sage.middleware.components.sage_mem.neuromem
- Add namespace marker files (__init__.py with pkgutil.extend_path)
- Update import paths in examples, tests, and documentation
- Update pyproject.toml package configuration
- Bump version to 0.2.0 (breaking change)

BREAKING CHANGE: Import path changed from 'neuromem' to 'sage.middleware.components.sage_mem.neuromem'
"
```

## 验证清单

重构完成后，确认以下事项：

- [ ] 目录结构正确：`sage/middleware/components/sage_mem/neuromem/`
- [ ] 命名空间标记文件存在且内容正确（4 个 `__init__.py`）
- [ ] `pyproject.toml` 的 `include` 已更新
- [ ] 所有 examples 导入路径已更新
- [ ] 所有 tests 导入路径已更新
- [ ] README.md 文档已更新
- [ ] `python3 -m build` 构建成功
- [ ] `pip install -e .` 安装成功
- [ ] 可以导入：`from sage.middleware.components.sage_mem.neuromem import MemoryManager`
- [ ] 所有测试通过：`pytest tests/`
- [ ] Git 提交已完成

## 兼容性说明

### Breaking Changes

- **导入路径变化**：
  - 旧：`from neuromem import MemoryManager`
  - 新：`from sage.middleware.components.sage_mem.neuromem import MemoryManager`

- **包名保持不变**：`isage-neuromem` (PyPI)

- **版本号**：建议升级到 `0.2.0`

### 迁移影响

**SAGE 主仓库**：
- ✅ 无需修改（已使用命名空间路径）

**外部用户**：
- ❌ 如果直接使用 `from neuromem import ...`，需要更新导入语句

### 向后兼容方案（可选）

如果需要保持向后兼容，可以在 `sage/middleware/components/sage_mem/neuromem/__init__.py` 中添加警告：

```python
import warnings

# 发出 deprecation warning
warnings.warn(
    "Direct import from 'neuromem' is deprecated. "
    "Please use 'from sage.middleware.components.sage_mem.neuromem import ...' instead. "
    "Support for old import path will be removed in version 0.3.0.",
    DeprecationWarning,
    stacklevel=2
)
```

## 故障排除

### 问题 1: 导入失败 `ModuleNotFoundError: No module named 'sage'`

**原因**：命名空间标记文件缺失

**解决**：检查 `sage/__init__.py` 等文件是否存在，内容是否正确

### 问题 2: `find_packages()` 找不到包

**原因**：`pyproject.toml` 配置错误

**解决**：
```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["sage.middleware.components.sage_mem.neuromem*"]
```

### 问题 3: 测试失败

**原因**：导入路径未更新

**解决**：使用 grep 查找所有旧的导入：
```bash
grep -r "from neuromem" tests/
grep -r "import neuromem" tests/
```

### 问题 4: Git 历史丢失

**原因**：使用 `mv` 而不是 `git mv`

**解决**：Git 通常能自动检测文件移动，但最好使用 `git mv`

## 参考资料

- [Python 命名空间包 (PEP 420)](https://peps.python.org/pep-0420/)
- [pkgutil.extend_path](https://docs.python.org/3/library/pkgutil.html#pkgutil.extend_path)
- [Setuptools Namespace Packages](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#namespace-packages)

## 联系支持

如有问题，请联系：
- Email: shuhao_zhang@hust.edu.cn
- GitHub Issues: https://github.com/intellistream/NeuroMem/issues

---

**最后更新**: 2026-01-05
**文档版本**: 1.0
