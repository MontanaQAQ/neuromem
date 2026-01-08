# NeuroMem Collection 重构实施指南

> **目标**: 将 6 个冗余的 Collection 类统一为唯一的 `UnifiedCollection`  
> **时间**: 5 周  
> **版本**: v0.3.0.0（Breaking Change）  
> **日期**: 2026-01-08 开始

---

## 📚 必读文件（按顺序）

### 第一步：理解背景和决策（30 分钟）

1. **[REFACTOR_SUMMARY.md](./REFACTOR_SUMMARY.md)** ⭐ 先看这个
   - 了解为什么要重构
   - 了解当前问题和目标架构
   - 快速决策指南

2. **[REFACTOR_DECISION.md](./REFACTOR_DECISION.md)**
   - 详细的决策矩阵
   - 风险评估
   - 三个方案对比（已选择方案 A）

3. **[CODE_REDUNDANCY_ANALYSIS.md](./CODE_REDUNDANCY_ANALYSIS.md)**
   - 代码冗余分析（4,200 行重复代码）
   - 各个 Collection 的功能对比

### 第二步：理解当前架构（1 小时）

4. **核心代码文件**（按重要性排序）：
   ```bash
   # 正确的实现（要保留）
   sage/neuromem/memory_collection/unified_collection.py          # ✅ 核心！399行

   # 冗余的实现（要删除）
   sage/neuromem/memory_collection/base_collection.py            # ❌ 384行
   sage/neuromem/memory_collection/vdb_collection.py             # ❌ 1,439行
   sage/neuromem/memory_collection/graph_collection.py           # ❌ 729行
   sage/neuromem/memory_collection/kv_collection.py              # ❌ 未知行数
   sage/neuromem/memory_collection/hybrid_collection.py          # ❌ 1,161行
   sage/neuromem/memory_collection/enhanced_collections.py       # ❌ paper features

   # Service 层（已迁移完成，无需修改）
   sage/neuromem/services/base_service.py                        # 所有 Service 的父类
   sage/neuromem/services/partitional/fifo_queue_service.py      # Service 示例

   # 管理器（无需修改）
   sage/neuromem/memory_manager.py                               # Collection 生命周期管理
   ```

### 第三步：查看详细实施计划（1 小时）

5. **[REFACTOR_PLAN_V2.md](./REFACTOR_PLAN_V2.md)** ⭐ 实施手册
   - 完整的 5 周计划
   - 每个任务的详细步骤
   - 代码实现示例
   - 迁移指南模板

---

## 🎯 你的任务（5 周计划）

### Week 1: 准备阶段（标记 + 增强）

#### 任务 1.1: 标记旧 Collection 为 Deprecated
**时间**: 2 小时

在以下 6 个文件的类定义开头添加 `DeprecationWarning`：

```python
# 需要修改的文件
sage/neuromem/memory_collection/base_collection.py
sage/neuromem/memory_collection/vdb_collection.py
sage/neuromem/memory_collection/graph_collection.py
sage/neuromem/memory_collection/kv_collection.py
sage/neuromem/memory_collection/hybrid_collection.py
sage/neuromem/memory_collection/enhanced_collections.py
```

**代码模板**（添加到每个类的 `__init__` 方法开头）：
```python
import warnings

class VDBMemoryCollection(BaseMemoryCollection):
    """[DEPRECATED] Will be removed in v0.3.0.0. Use UnifiedCollection instead."""

    def __init__(self, config: dict):
        warnings.warn(
            "VDBMemoryCollection is deprecated and will be removed in v0.3.0.0. "
            "Use UnifiedCollection instead. See docs/dev-note/MIGRATION_GUIDE.md",
            DeprecationWarning,
            stacklevel=2
        )
        # ... 原有代码
```

**验证**：运行测试，确保能看到警告：
```bash
pytest tests/test_hybrid_collection.py -v
```

---

#### 任务 1.2: 实现可插拔存储后端
**时间**: 1 天

创建新文件：`sage/neuromem/storage_engine/storage_factory.py`

**参考**：见 [REFACTOR_PLAN_V2.md](./REFACTOR_PLAN_V2.md) 第 3.2 节（完整代码）

**需要实现**：
1. `StorageBackend` 抽象接口
2. `MemoryStorage` 实现（必须）
3. `RedisStorage` 实现（可选）
4. `SageDBStorage` 实现（可选）
5. `StorageFactory` 工厂类

**修改**：增强 `UnifiedCollection.__init__()`
```python
# sage/neuromem/memory_collection/unified_collection.py

def __init__(
    self,
    name: str,
    storage_backend: str = "memory",      # 新增参数
    storage_config: dict | None = None,   # 新增参数
    config: dict | None = None
):
    self.name = name
    self.config = config or {}

    # 新增：使用可插拔存储
    from ..storage_engine.storage_factory import StorageFactory
    self.storage = StorageFactory.create(storage_backend, storage_config)

    # 原有代码
    self.indexes: dict[str, Any] = {}
    self.index_metadata: dict[str, dict[str, Any]] = {}
```

**验证**：
```bash
# 测试内存存储
python -c "
from sage.neuromem import UnifiedCollection
c = UnifiedCollection('test', storage_backend='memory')
c.insert('hello', {})
print(c.get(list(c.storage.keys())[0]))
"
```

---

#### 任务 1.3: 创建迁移文档
**时间**: 4 小时

创建文件：`docs/dev-note/MIGRATION_GUIDE.md`

**内容结构**：
```markdown
# Collection 迁移指南 (v0.2.x → v0.3.0.0)

## 概述
v0.3.0.0 统一所有 Collection 为 UnifiedCollection

## 迁移映射

### VDBMemoryCollection → UnifiedCollection
[之前代码] → [之后代码]

### GraphMemoryCollection → UnifiedCollection
[之前代码] → [之后代码]

### HybridCollection → UnifiedCollection
[之前代码] → [之后代码]

## 常见问题
...
```

**参考**：见 [REFACTOR_PLAN_V2.md](./REFACTOR_PLAN_V2.md) 任务 1.2 的模板

---

### Week 2-3: 测试迁移

#### 任务 2.1: 迁移 Collection 单元测试
**时间**: 3 天

**目标**：合并所有旧测试到新文件

```bash
# 创建新测试文件
touch tests/unit/neuromem/test_unified_collection_complete.py
```

**需要合并的测试**：
```bash
tests/components/sage_mem/test_vdb_collection.py      → VectorIndexes 测试
tests/components/sage_mem/test_graph_collection.py    → GraphIndexes 测试
tests/components/sage_mem/test_kv_collection.py       → KVIndexes 测试
tests/test_hybrid_collection.py                       → MultiIndex 测试
```

**代码结构**：
```python
# tests/unit/neuromem/test_unified_collection_complete.py

class TestUnifiedCollectionVectorIndexes:
    """原 VDBMemoryCollection 的测试"""

    def test_faiss_index(self):
        collection = UnifiedCollection("test_faiss")
        collection.add_index("vec", "faiss", {"dim": 768})
        # ... 测试逻辑

class TestUnifiedCollectionGraphIndexes:
    """原 GraphMemoryCollection 的测试"""
    # ...

class TestUnifiedCollectionMultiIndex:
    """原 HybridCollection 的测试"""
    # ...
```

**验证**：
```bash
pytest tests/unit/neuromem/test_unified_collection_complete.py -v
```

---

#### 任务 2.2: 迁移 Paper Features 测试
**时间**: 2 天

**目标**：将 Paper Features 重构为 Mixin 模式

**修改文件**：`tests/test_paper_features.py`

**之前**：
```python
collection = VDBMemoryCollectionWithFeatures({"name": "test"})
```

**之后**（Mixin 模式）：
```python
from sage.neuromem.memory_collection import UnifiedCollection
from sage.neuromem.memory_collection.paper_features import TripleStorageMixin

class EnhancedCollection(UnifiedCollection, TripleStorageMixin):
    pass

collection = EnhancedCollection("test")
```

**验证**：
```bash
pytest tests/test_paper_features.py -v
```

---

### Week 4: 代码清理

#### 任务 4.1: 删除旧 Collection 文件
**时间**: 1 小时

**⚠️ 重要**：在删除前确保所有测试已迁移！

```bash
# 删除冗余文件
rm sage/neuromem/memory_collection/base_collection.py
rm sage/neuromem/memory_collection/vdb_collection.py
rm sage/neuromem/memory_collection/graph_collection.py
rm sage/neuromem/memory_collection/kv_collection.py
rm sage/neuromem/memory_collection/hybrid_collection.py
rm sage/neuromem/memory_collection/enhanced_collections.py

# 删除旧测试
rm tests/components/sage_mem/test_vdb_collection.py
rm tests/components/sage_mem/test_graph_collection.py
rm tests/components/sage_mem/test_kv_collection.py
rm tests/test_hybrid_collection.py
```

**验证**：确保项目仍能运行
```bash
pytest tests/unit/neuromem/ -v
pytest tests/integration/ -v
```

---

#### 任务 4.2: 更新 __init__.py
**时间**: 30 分钟

**修改文件**：`sage/neuromem/memory_collection/__init__.py`

**新内容**：
```python
"""
Memory Collection Module - 统一数据容器

v0.3.0.0 重大变更:
- 移除 BaseMemoryCollection, VDBMemoryCollection 等
- 统一使用 UnifiedCollection
- 支持可插拔存储后端（Memory/Redis/SageDB）
"""

from .unified_collection import UnifiedCollection

# Paper features (通过 Mixin 实现)
from .paper_features import (
    TripleStorageMixin,
    LinkEvolutionMixin,
    ConflictDetectionMixin,
    # ... 其他 mixins
)

__all__ = [
    "UnifiedCollection",
    "TripleStorageMixin",
    "LinkEvolutionMixin",
    "ConflictDetectionMixin",
]
```

---

### Week 5: 文档和发布

#### 任务 5.1: 更新文档
**时间**: 1 天

需要更新的文件：
```bash
README.md                           # 快速开始示例
docs/README.md                      # 主文档
sage/neuromem/services/API_REFERENCE.md  # API 参考
docs/CONTRIBUTING.md                # 开发指南
CHANGELOG.md                        # 变更日志
.github/copilot-instructions.md     # Copilot 指令
```

**关键点**：
- 所有示例代码改用 `UnifiedCollection`
- 添加存储后端配置示例
- 高亮 Breaking Change

---

#### 任务 5.2: 发布 v0.3.0.0
**时间**: 2 小时

**步骤**：

1. **更新版本号**（4 位语义版本）：
   ```bash
   # 修改这两个文件
   vim pyproject.toml              # version = "0.3.0.0"
   vim sage/neuromem/_version.py   # __version__ = "0.3.0.0"
   ```

2. **提交代码**：
   ```bash
   git add .
   git commit -m "refactor: unify all collections into UnifiedCollection (Breaking Change)

   BREAKING CHANGE:
   - Removed: VDBMemoryCollection, GraphMemoryCollection, KVMemoryCollection, HybridCollection
   - Use UnifiedCollection instead
   - See docs/dev-note/MIGRATION_GUIDE.md for migration guide
   "
   git tag v0.3.0.0
   git push origin main-dev --tags
   ```

3. **运行完整测试**：
   ```bash
   pytest tests/ -v --cov=sage/neuromem --cov-report=term
   ```

4. **发布到 PyPI**：
   ```bash
   cd /home/zrc/develop_item/bench/neuromem
   sage-pypi-publisher build . -o /tmp/neuromem-build -u -r pypi --no-dry-run
   ```

5. **验证发布**：
   ```bash
   pip index versions isage-neuromem
   # 应该看到 0.3.0.0
   ```

---

## 🔍 关键检查点

### Week 1 结束时
- [ ] 所有旧 Collection 显示 DeprecationWarning
- [ ] StorageFactory 实现完成（至少 Memory）
- [ ] MIGRATION_GUIDE.md 创建完成

### Week 2-3 结束时
- [ ] `test_unified_collection_complete.py` 通过
- [ ] `test_paper_features.py` 使用 Mixin 模式
- [ ] 测试覆盖率 > 90%

### Week 4 结束时
- [ ] 6 个旧 Collection 文件已删除
- [ ] `__init__.py` 只导出 UnifiedCollection
- [ ] 所有测试仍然通过

### Week 5 结束时
- [ ] 所有文档更新完成
- [ ] v0.3.0.0 成功发布到 PyPI
- [ ] Release Notes 发布

---

## 🛠 常用命令

### 查看代码冗余
```bash
# 统计行数
wc -l sage/neuromem/memory_collection/*.py

# 搜索旧 Collection 使用
rg "VDBMemoryCollection|GraphMemoryCollection|HybridCollection" --type py

# 查看导入情况
rg "from.*memory_collection import" --type py
```

### 运行测试
```bash
# 完整测试
pytest tests/ -v

# Collection 测试
pytest tests/unit/neuromem/ -v

# 单个测试文件
pytest tests/test_paper_features.py -v -k "test_triple"

# 带覆盖率
pytest tests/ --cov=sage/neuromem --cov-report=html
```

### 代码检查
```bash
# 类型检查
mypy sage/neuromem/memory_collection/

# 格式检查
ruff check sage/neuromem/

# 格式化
ruff format sage/neuromem/
```

---

## ⚠️ 注意事项

### 不要做的事情

1. **不要修改 Service 层代码**
   - Service 已经使用 `UnifiedCollection`
   - Service API 保持不变

2. **不要修改 MemoryManager**
   - MemoryManager 只管理 `UnifiedCollection`
   - API 保持兼容

3. **不要删除 Paper Features 功能**
   - 重构为 Mixin 模式，但功能必须保留
   - 所有 paper_features 测试必须通过

### 一定要做的事情

1. **确保测试覆盖率 > 90%**
   - 运行 `pytest --cov` 检查
   - 合并测试时不要丢失测试用例

2. **在 CHANGELOG.md 中高亮 Breaking Change**
   ```markdown
   ## [0.3.0.0] - 2026-02-15

   ### BREAKING CHANGES
   - Removed all legacy Collection classes
   - Use UnifiedCollection instead
   - See MIGRATION_GUIDE.md
   ```

3. **提供清晰的迁移指南**
   - 每种旧 Collection 都要有示例
   - 包含常见问题解答

---

## 📞 遇到问题？

### 阅读顺序
1. 先看 [REFACTOR_SUMMARY.md](./REFACTOR_SUMMARY.md) - 快速理解
2. 遇到问题查 [REFACTOR_PLAN_V2.md](./REFACTOR_PLAN_V2.md) - 详细方案
3. 技术细节看代码注释和测试

### 关键文件
- 核心实现：`unified_collection.py`（399 行，已验证）
- Service 示例：`fifo_queue_service.py`（已正确使用 UnifiedCollection）
- 测试参考：`tests/unit/neuromem/test_unified_collection_basic.py`

### 验证方法
每完成一个任务，运行对应的测试确保没有破坏现有功能。

---

## ✅ 成功标准

完成后，项目应该：
- ✅ 只有 1 个 Collection 类（`UnifiedCollection`）
- ✅ 代码减少约 6,000 行
- ✅ 所有测试通过（覆盖率 > 90%）
- ✅ 文档更新完成
- ✅ 成功发布到 PyPI

---

**祝你实施顺利！有任何问题可以参考详细计划文档。** 🚀
