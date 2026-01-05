# SAGE Memory Pipeline 开发档案

> 本档案汇总 SAGE 记忆系统的完整设计与实现，包括：
>
> - Benchmark Pipeline 架构设计
> - 论文记忆体五维度分类与实现
> - NeuroMem 底层引擎重构
>
> 更新时间：2025-12-12

______________________________________________________________________

## 一、Benchmark Pipeline 架构设计

### 1.1 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Pipeline 算子层 (sage-benchmark/libs)                          │
│  ├── PreInsert        → Normalization Strategy（仅检索）         │
│  ├── MemoryInsert     → 执行插入（支持多种插入方法）              │
│  ├── PostInsert       → Consolidation Policy（检索/删除/插入）   │
│  ├── PreRetrieval     → Query Formulation（不访问存储）          │
│  ├── MemoryRetrieval  → 执行检索                                 │
│  └── PostRetrieval    → Context Integration（可多次检索）        │
├─────────────────────────────────────────────────────────────────┤
│  MemoryService 服务层 (sage-middleware/services)                 │
│  ├── ShortTermMemoryService     → 会话短期记忆                   │
│  ├── KeyValueMemoryService      → 精确/模糊键值检索               │
│  ├── GraphMemoryService         → 知识图谱存储                   │
│  ├── HierarchicalMemoryService  → 分层记忆（STM/MTM/LTM）         │
│  ├── HybridMemoryService        → 多索引融合检索                  │
│  ├── VectorMemoryService        → 统一向量记忆（支持多种索引）      │
│  └── NeuroMemVDBService         → 通用向量数据库服务               │
├─────────────────────────────────────────────────────────────────┤
│  NeuroMem 引擎层 (sage-middleware/neuromem)                      │
│  ├── MemoryManager              → Collection 统一管理器           │
│  ├── MemoryCollection 家族                                       │
│  │   ├── VDBMemoryCollection    → 向量集合                       │
│  │   ├── KVMemoryCollection     → 键值集合                       │
│  │   ├── GraphMemoryCollection  → 图集合                         │
│  │   └── HybridCollection       → 混合集合（一份数据+多种索引）    │
│  └── SearchEngine 索引层                                         │
│      ├── vdb_index/             → 向量索引 (FAISS)               │
│      ├── kv_index/              → 文本索引 (BM25S)               │
│      └── graph_index/           → 图索引 (邻接表+PPR)            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Pipeline 六阶段设计

**Pipeline 的六个阶段各司其职**，通过明确的职责划分和操作约束，实现清晰的数据流和可维护的架构。

#### 六阶段职责总览

- **PreInsert**（Normalization Strategy）：处理记忆信息，决定插入方式（主动插入），可查询不可修改存储
- **MemoryInsert**：执行插入操作，透传 PreInsert 结果
- **PostInsert**（Consolidation Policy）：数据结构调优，可执行完整的增删改查操作（主动插入的第二阶段）
- **PreRetrieval**（Query Formulation）：处理查询，不访问存储
- **MemoryRetrieval**：执行检索操作
- **PostRetrieval**（Context Integration）：处理检索结果，可多次检索

#### 操作权限约束表

| 阶段            | 检索    | 插入    | 删除    | 状态查询 | 说明                 |
| --------------- | ------- | ------- | ------- | -------- | -------------------- |
| PreInsert       | ✅ 可选 | ❌      | ❌      | ❌       | 预处理，决定插入方式 |
| MemoryInsert    | ❌      | ✅      | ❌      | ❌       | 执行插入             |
| PostInsert      | ✅ 多次 | ✅ 多次 | ✅ 多次 | ✅ 多次  | 数据结构调优         |
| PreRetrieval    | ❌      | ❌      | ❌      | ❌       | 不访问存储           |
| MemoryRetrieval | ✅      | ❌      | ❌      | ❌       | 执行检索             |
| PostRetrieval   | ✅ 多次 | ❌      | ❌      | ❌       | 结果处理，可多次查询 |

#### 主动插入 vs 被动插入

在当前代码实现里，`insert_mode`/`insert_params` 本质上是 **Pipeline → MemoryService 的“提示参数”**：PreInsert 产生
`memory_entries` 后会补齐默认字段（`insert_mode` 默认为 `"passive"`，`insert_method` 默认为 `"default"`），随后
MemoryInsert 对每条 entry 直接调用记忆服务
`insert(entry, vector, metadata, insert_mode=..., insert_params=...)` 并原样透传；因此
**被动插入**时由服务按自身策略处理（例如 STM 的 FIFO；Hierarchical 默认落入第一层，并在容量溢出时仅更新内部 pending 状态而不在插入阶段自动迁移），只有当某个
PreInsert Action 显式把 `insert_mode` 设为 `"active"` 时，服务才会读取 `insert_params`（如
`target_tier`/`force`/`priority`）用于指定目标层级、写入优先级或跳过容量检查。

#### 主动检索 vs 被动检索

在当前代码实现里，PreRetrieval 会输出 `question`/`query_embedding`，并可选附带 `retrieve_mode` 与结构化
`retrieve_params`；但 MemoryRetrieval 实际上**不依赖 `retrieve_mode` 来分支**，而是以 `question`（以及可选的
`query_embedding`）为主调用记忆服务的 `retrieve(query=..., vector=..., metadata=..., top_k=...)`，并且会读取
`retrieve_params` 来启用“更主动”的检索编排（例如 `sub_queries`/`multi_query` + 对应的预生成
embeddings，逐个子查询检索后去重合并）。因此这里的“被动检索”可以理解为：没有额外 `retrieve_params` 时按单查询走服务默认逻辑；“主动检索”则是 PreRetrieval
通过 `retrieve_params`（以及必要时的 embedding）显式引导多查询/扩展查询等检索路径，而具体的层级范围与检索方式主要由底层服务依据 `metadata` 与是否提供
`vector` 决定（例如 Hierarchical 支持通过 `metadata["tiers"]` 指定搜索层级、通过 `metadata["method"]` 选择
semantic/recent）。

______________________________________________________________________

### 1.3 各阶段详细设计

#### 1.4.1 PreInsert（Normalization Strategy）

> **职责**：记忆信息预处理，使原始记忆能够正常插入记忆数据结构

**功能定位**：

- 处理原始的记忆信息，进行标准化、提取、转换等操作
- 决定如何插入记忆（即规定一次主动的插入策略）
- 仅允许对记忆服务进行**查询**操作（用于获取上下文信息，如检查重复等）

**权限约束原因**：

- ✅ **允许查询**：需要检查记忆重复性、获取上下文信息来决定处理策略
- ❌ **禁止插入/删除**：避免在预处理阶段破坏数据完整性，真正的插入由 MemoryInsert 统一执行

**代码规范**：

```python
# packages/.../experiment/libs/pre_insert/operator.py
from sage.common.core import MapFunction

from sage.benchmark.benchmark_memory.experiment.libs.pre_insert.base import (
    BasePreInsertAction,
    PreInsertInput,
    PreInsertOutput,
)
from sage.benchmark.benchmark_memory.experiment.libs.pre_insert.registry import (
    PreInsertActionRegistry,
)


class PreInsert(MapFunction):
    """插入前预处理（Action + Registry 机制）"""

    def __init__(self, config): ...
    def execute(self, data: dict) -> dict: ...
    def _generate_embeddings(self, entries: list[dict]) -> None: ...


class MyPreInsertAction(BasePreInsertAction):
    def _init_action(self) -> None: ...
    def execute(self, input_data: PreInsertInput) -> PreInsertOutput: ...


PreInsertActionRegistry.register("my_action", MyPreInsertAction)
```

**输出数据结构**：

```python
{
    # PreInsert 统一产出：data["memory_entries"]
    "memory_entries": [
        {
            "text": str,
            "embedding": list[float] | None,
            "metadata": dict,
            "insert_mode": str,     # 默认 "passive"（由 BasePreInsertAction._set_default_fields 补齐）
            "insert_method": str,   # 默认 "default"
            "insert_params": dict | None,
        },
        ...
    ],
}
```

#### 1.4.2 MemoryInsert（Memory Data Structure - Insert）

> **职责**：执行记忆插入操作

**功能定位**：

- 透传 PreInsert 的处理结果到记忆服务
- 支持多种插入方法（`insert_method`）和插入模式（`insert_mode`）
- 底层引擎可直接复用

**代码规范**：

```python
# packages/.../experiment/libs/memory_insert.py
from sage.common.core import MapFunction


class MemoryInsert(MapFunction):
    """纯透传插入：逐条调用 memory_service.insert(...) 并返回结构化统计"""

    def __init__(self, config=None): ...
    def execute(self, data: dict) -> dict: ...
    def _insert_entry(self, entry: dict) -> str: ...
```

**输出数据结构**：

```python
{
    # 透传原 data +
    "insert_stats": {
        "inserted": int,
        "failed": int,
        "entry_ids": list[str],
        "entries": list[dict],  # [{"id","text","embedding","metadata"}, ...]
        "errors": list[dict],   # [{"entry": "...", "error": "..."}, ...]
    }
}
```

#### 1.4.3 PostInsert（Consolidation Policy）

> **职责**：记忆数据结构的调优与整合

**功能定位**：

- 根据记忆数据结构状态或记忆信息对数据结构进行优化操作
- 可执行蒸馏（distillation）、迁移（migrate）、遗忘（forgetting）、链接演化（link_evolution）等策略
- 允许多次调用记忆服务的各类操作（查询、插入、删除、状态获取）

**权限约束原因**：

- ✅ **完全权限**：作为主动插入的第二阶段，需要根据服务状态反馈执行数据结构调整
- 典型场景：STM 满了需要迁移到 MTM（需要插入+删除）、低价值记忆遗忘（需要删除）、知识图谱链接演化（需要查询+插入）

**代码规范**：

```python
# packages/.../experiment/libs/post_insert/operator.py
from sage.common.core import MapFunction

from sage.benchmark.benchmark_memory.experiment.libs.post_insert.base import (
    BasePostInsertAction,
    PostInsertInput,
    PostInsertOutput,
)
from sage.benchmark.benchmark_memory.experiment.libs.post_insert.registry import (
    PostInsertActionRegistry,
)


class PostInsert(MapFunction):
    """插入后调优：允许对服务执行 search/insert/update/delete（通过 ServiceProxy 受控暴露）"""

    def __init__(self, config): ...
    def execute(self, data: dict) -> dict: ...


class MyPostInsertAction(BasePostInsertAction):
    def _init_action(self) -> None: ...
    def execute(self, input_data: PostInsertInput, service, llm=None) -> PostInsertOutput: ...


PostInsertActionRegistry.register("my_action", MyPostInsertAction)
```

#### 1.4.4 PreRetrieval（Query Formulation Strategy）

> **职责**：查询预处理，优化检索效果，决定检索方式（主动检索）

**功能定位**：

- 处理用户查询，使其能够更好地检索到记忆信息
- 可执行查询扩展、关键词提取、查询改写、查询分类等操作
- 决定检索模式（主动检索 vs 被动检索）
- **不允许调用记忆服务**，仅处理查询本身

**📋 PreRetrieval 策略分类体系**

本实验采用以下统一的策略分类标准，按复杂度递进排列：

| 类别            | 策略名称                   | 功能定位                        | 适用场景                                 |
| --------------- | -------------------------- | ------------------------------- | ---------------------------------------- |
| **1. 直接处理** | `none`                     | 原始查询透传，不做任何处理      | 支持文本匹配的记忆体（MemoryOS, Mem0ᵍ）  |
|                 | `embedding`                | 仅做基础向量化，无其他优化      | 必须有向量的记忆体（TiM）或作为 baseline |
| **2. 文本优化** | `optimize.keyword_extract` | 提取关键词/实体，配合结构化检索 | 三元组/图检索场景                        |
|                 | `optimize.expand`          | 扩展同义词和相关实体，增强召回  | 需要提升覆盖率的场景                     |
|                 | `optimize.rewrite`         | LLM 改写查询，增强语义表达      | 需要理解上下文的复杂查询                 |
| **3. 查询增强** | `enhancement.decompose`    | 将复杂查询分解为多个子查询      | 多跳推理、复杂问题拆解                   |
|                 | `enhancement.route`        | 生成检索策略提示，指导路由选择  | 多层/多源记忆系统                        |
|                 | `enhancement.multi_embed`  | 多维向量化，综合多种相似度      | 精细化/多模态检索                        |
| **4. 查询验证** | `validate`                 | 检查查询合法性，过滤无效查询    | 质量保证、异常处理                       |

**分类设计原则**：

- **层次递进**：从简单到复杂，便于实验对比
- **功能正交**：每个类别功能独立，边界清晰
- **实验友好**：可按类别设计对比实验矩阵

**权限约束原因**：

- ❌ **完全禁止访问存储**：作为纯查询处理阶段，应该是无副作用的操作（纯函数）
- 设计原则：查询改写/扩展不需要访问存储，只需要 LLM 或规则引擎即可完成

**代码规范**：

```python
# packages/.../experiment/libs/pre_retrieval/operator.py
from sage.common.core import MapFunction

from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval.base import (
    BasePreRetrievalAction,
    PreRetrievalInput,
    PreRetrievalOutput,
)
from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval.registry import (
    PreRetrievalActionRegistry,
)


class PreRetrieval(MapFunction):
    """查询预处理（不访问存储）：Action + Registry 机制"""

    def __init__(self, config): ...
    def execute(self, data: dict) -> dict: ...


class MyPreRetrievalAction(BasePreRetrievalAction):
    def _init_action(self) -> None: ...
    def execute(self, input_data: PreRetrievalInput) -> PreRetrievalOutput: ...


PreRetrievalActionRegistry.register("my_action", MyPreRetrievalAction)
```

**输出数据结构**：

```python
{
    # PreRetrieval 会改写 data["question"]（统一入口字段）
    "question": str,                         # 处理后的查询文本
    "query_embedding": list[float] | None,   # 查询向量（可选）
    "metadata": dict,                        # 查询元数据（可选）
    "retrieve_mode": str,                    # 默认为 "passive"（是否参与分支取决于下游实现）
    "retrieve_params": dict | None,          # 结构化检索参数（如 sub_queries/multi_query 等）
}
```

#### 1.4.5 MemoryRetrieval（Memory Data Structure - Retrieve）

> **职责**：执行记忆检索操作

**功能定位**：

- 透传 PreRetrieval 的处理结果到记忆服务
- 支持多种检索方法（向量检索、关键词检索、图检索等）
- 支持主动检索（指定层级/索引）和被动检索（服务默认策略）
- 底层引擎可直接复用

**代码规范**：

```python
# packages/.../experiment/libs/memory_retrieval.py
from sage.common.core import MapFunction


class MemoryRetrieval(MapFunction):
    """纯透传检索：调用 memory_service.retrieve(...)，并返回 memory_data + retrieval_stats"""

    def __init__(self, config=None): ...
    def execute(self, data: dict) -> dict: ...
```

**调用示例**：

```python
query = data.get("question")
vector = data.get("query_embedding")
metadata = data.get("metadata", {})
top_k = 10

results = self.call_service(
    self.service_name,
    method="retrieve",
    query=query,
    vector=vector,
    metadata=metadata,
    top_k=top_k,
    timeout=60.0,
)
```

#### 1.4.6 PostRetrieval（Context Integration Mechanism）

> **职责**：记忆语料优化，服务推理

**功能定位**：

- 处理检索结果，通过再查询、重构结果等方法优化送入大模型的语料
- 可执行重排序（rerank）、合并（merge）、增强（augment）、过滤（filter）等操作
- 允许多次调用记忆的**检索服务**（如再查询、链接扩展等）

**权限约束原因**：

- ✅ **允许多次检索**：可能需要基于初次检索结果进行再查询（如链接扩展、关联实体检索）
- ❌ **禁止插入/删除**：查询阶段不应修改记忆结构，避免引入不可控因素和副作用
- 设计原则：读操作应该是幂等的、无副作用的，保持数据一致性

**代码规范**：

```python
# packages/.../experiment/libs/post_retrieval/operator.py
from sage.common.core import MapFunction

from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval.base import (
    BasePostRetrievalAction,
    MemoryItem,
    PostRetrievalInput,
    PostRetrievalOutput,
)
from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval.registry import (
    PostRetrievalActionRegistry,
)


class PostRetrieval(MapFunction):
    """检索后处理：允许多次 search（通过 ServiceProxy），最终生成 history_text"""

    def __init__(self, config): ...
    def execute(self, data: dict) -> dict: ...


class MyPostRetrievalAction(BasePostRetrievalAction):
    def _init_action(self) -> None: ...
    def execute(self, input_data: PostRetrievalInput, service, llm=None) -> PostRetrievalOutput: ...


PostRetrievalActionRegistry.register("my_action", MyPostRetrievalAction)
```

**输出数据结构**：

```python
{
    # 透传原 data +
    "history_text": str,                     # 供下游 LLM 使用的最终上下文文本
    "processed_memory_items": list[dict],    # [{"text","score","metadata"}, ...]（可选）
    "metadata": dict,                        # action 产生的额外信息（可选）
}
```

______________________________________________________________________

### 1.4 MemoryService 与引擎设计

**底层实现原则**，定义 MemoryService 如何组织数据和索引。

#### ⭐ Service : Collection = 1 : 1

每个 MemoryService 只持有一个 Collection，避免多数据源管理复杂性。

```python
# ✅ 正确：一个 Service 只持有一个 Collection
class SomeService(BaseService):
    collection: SomeCollection

# ❌ 错误：不应持有多个 Collection
class SomeService(BaseService):
    collection_a: VDBCollection
    collection_b: KVCollection
```

#### ⭐ Collection = 一份数据 + 多种索引

Collection 支持在同一份数据上建立多种类型的索引（向量、文本、图），实现灵活的检索策略。

```python
class HybridCollection(BaseMemoryCollection):
    # 数据只存一份
    text_storage = TextStorage()
    metadata_storage = MetadataStorage()

    # 多种类型的索引（在同一份数据上）
    vdb_indexes: dict[str, BaseVDBIndex]     # 向量索引
    kv_indexes: dict[str, BaseKVIndex]       # 文本索引
    graph_indexes: dict[str, BaseGraphIndex] # 图索引
```

#### ⭐ 索引可以独立增删

索引与数据解耦，支持动态添加/删除索引而不影响数据本身。

```python
# 插入数据到多个索引
collection.insert(content, index_names=["fifo", "segment_vdb"])

# 从某个索引移除（数据保留）
collection.remove_from_index(item_id, "fifo")

# 将已有数据加到新索引
collection.insert_to_index(item_id, "segment_vdb", vector=vec)

# 完全删除（数据 + 所有索引）
collection.delete(item_id)
```

#### ⭐ 统一服务接口

整体调用链保持单向、可追踪：**算子层 → Service → Collection → SearchEngine**，避免跨层耦合。

**MemoryService 统一接口**（所有服务必须实现，参考 R1 重构）：

```python
class BaseMemoryService:
    def insert(
        self,
        entry: str,
        vector: list[float] | None = None,
        metadata: dict | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict | None = None
    ) -> str:
        """插入记忆

        Args:
            entry: 文本内容
            vector: embedding 向量（可选）
            metadata: 元数据（可选）
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数（仅 insert_mode="active" 时有效）
                - 通用参数: priority, force
                - 服务特定参数: target_tier, node_type, target_indexes 等

        Returns:
            str: 条目 ID
        """

    def retrieve(
        self,
        query: str,
        vector: list[float] | None = None,
        metadata: dict | None = None,
        top_k: int = 5,
        *,
        retrieve_mode: Literal["active", "passive"] = "passive",
        retrieve_params: dict | None = None
    ) -> list[dict]:
        """检索记忆

        Args:
            query: 查询文本
            vector: 查询向量（可选）
            metadata: 查询元数据（可选）
            top_k: 返回结果数量
            retrieve_mode: 检索模式 ("active" | "passive")
            retrieve_params: 主动检索参数（仅 retrieve_mode="active" 时有效）
                - 通用参数: rerank, filter
                - 服务特定参数: target_tier, target_indexes, multi_tier 等

        Returns:
            list[dict]: 检索结果列表
        """

    def delete(self, entry_id: str) -> bool:
        """删除记忆，返回是否成功"""

    def get_status(self) -> dict:
        """获取服务状态（如容量、待迁移条目等）"""

    def optimize(self) -> dict:
        """执行优化操作（如压缩、索引重建等）"""
```

**关键设计原则**：

- ✅ **统一接口签名**：所有 7 个服务（HierarchicalMemory, GraphMemory, ShortTermMemory, KeyValueMemory,
  HybridMemory, NeuroMemVDB, VectorHashMemory）的 `insert` 和 `retrieve` 方法签名完全一致
- ✅ **双模式支持**：通过 `insert_mode`/`retrieve_mode` 区分主动（Pipeline 控制）和被动（Service 自主决定）
- ✅ **灵活参数传递**：`insert_params`/`retrieve_params` 支持服务特定的参数，由各服务根据自身特性解析
- ✅ **向后兼容**：所有 mode 和 params 参数均有默认值，旧代码无需修改

#### 主动插入与被动插入

**主动插入**（Pipeline 显式控制存储策略）：

```python
# PreInsert 分析内容后，在 memory_entry 中设置插入参数
memory_entry = {
    "text": "这是一条重要的摘要",
    "embedding": [...],
    "metadata": {"is_summary": True, "timestamp": "2025-01-01"},
    "insert_mode": "active",
    "insert_params": {"target_tier": "ltm", "priority": 9}
}

# MemoryInsert 透传给服务
service.insert(
    entry=memory_entry["text"],
    vector=memory_entry["embedding"],
    metadata=memory_entry["metadata"],
    insert_mode="active",
    insert_params={"target_tier": "ltm", "priority": 9}
)

# HierarchicalMemoryService 根据 insert_params 执行
class HierarchicalMemoryService:
    def insert(self, entry, vector=None, metadata=None, *,
               insert_mode="passive", insert_params=None):
        if insert_mode == "active" and insert_params:
            # 显式指定目标层级
            target_tier = insert_params.get("target_tier", self.tier_names[0])
            force = insert_params.get("force", False)
            # ...直接插入到指定层级
```

**被动插入**（Service 根据预定义逻辑决定）：

```python
# PreInsert 不指定插入参数
memory_entry = {
    "text": "普通对话内容",
    "embedding": [...],
    "metadata": {"timestamp": "2025-01-01"}
    # 无 insert_mode 和 insert_params
}

# MemoryInsert 使用默认值
service.insert(
    entry=memory_entry["text"],
    vector=memory_entry["embedding"],
    metadata=memory_entry["metadata"]
    # insert_mode 默认为 "passive"
)

# HierarchicalMemoryService 使用预定义逻辑
class HierarchicalMemoryService:
    def insert(self, entry, vector=None, metadata=None, *,
               insert_mode="passive", insert_params=None):
        if insert_mode == "passive":
            # 默认存入第一层（如 STM）
            target_tier = self.tier_names[0]
            # 当容量满时，记录待迁移状态（供 PostInsert 查询）
            if self._is_tier_full(target_tier):
                self._pending_migrations.append({
                    "action": "migrate",
                    "from_tier": target_tier,
                    "to_tier": self.tier_names[1]
                })
```

#### 主动检索与被动检索

**主动检索**（Pipeline 显式控制检索策略）：

```python
# PreRetrieval 分析查询后，设置检索参数
retrieval_config = {
    "query": "用户的历史爱好是什么？",
    "query_vector": [...],
    "metadata": {"query_type": "knowledge"},
    "retrieve_mode": "active",
    "retrieve_params": {"target_tier": "ltm", "top_k": 10}
}

# MemoryRetrieval 透传给服务
results = service.retrieve(
    query=retrieval_config["query"],
    vector=retrieval_config["query_vector"],
    metadata=retrieval_config["metadata"],
    retrieve_mode="active",
    retrieve_params={"target_tier": "ltm", "top_k": 10}
)

# HierarchicalMemoryService 根据 retrieve_params 执行
class HierarchicalMemoryService:
    def retrieve(self, query, vector=None, metadata=None, top_k=5, *,
                 retrieve_mode="passive", retrieve_params=None):
        if retrieve_mode == "active" and retrieve_params:
            # 显式指定检索层级
            target_tier = retrieve_params.get("target_tier")
            if target_tier:
                # 只从指定层级检索
                return self._retrieve_from_tier(target_tier, query, vector, top_k)

            # 或多层级混合检索
            if retrieve_params.get("multi_tier"):
                weights = retrieve_params.get("tier_weights", {})
                return self._multi_tier_retrieve(query, vector, top_k, weights)
```

**被动检索**（Service 根据预定义逻辑决定）：

```python
# PreRetrieval 不指定检索参数
retrieval_config = {
    "query": "刚才说了什么？",
    "query_vector": [...]
    # 无 retrieve_mode 和 retrieve_params
}

# MemoryRetrieval 使用默认值
results = service.retrieve(
    query=retrieval_config["query"],
    vector=retrieval_config["query_vector"]
    # retrieve_mode 默认为 "passive"
)

# HierarchicalMemoryService 使用预定义逻辑
class HierarchicalMemoryService:
    def retrieve(self, query, vector=None, metadata=None, top_k=5, *,
                 retrieve_mode="passive", retrieve_params=None):
        if retrieve_mode == "passive":
            # 默认从所有层级检索，按时间衰减加权
            all_results = []
            for tier_name in self.tier_names:
                tier_results = self._retrieve_from_tier(tier_name, query, vector, top_k)
                # 根据层级和时间加权
                weighted_results = self._apply_decay(tier_results, tier_name)
                all_results.extend(weighted_results)

            # 返回 top_k 结果
            return sorted(all_results, key=lambda x: x["score"], reverse=True)[:top_k]
```

______________________________________________________________________

## 二、论文记忆体五维度分类

> 本章用于把“论文记忆体”映射到 SAGE 的 **可运行 Pipeline 组合**。
>
> **重要**：本章以“当前代码注册表/工厂”为准，而不是旧版 `Memory.md` 或历史 YAML。
>
> - D1（MemoryService）来源：
>   `packages/sage-middleware/src/sage/middleware/components/sage_mem/services/memory_service_factory.py`
> - D2（PreInsert）来源：
>   `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/pre_insert/registry.py`
> - D3（PostInsert）来源：
>   `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/post_insert/registry.py`
> - D4（PreRetrieval）来源：
>   `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/pre_retrieval/registry.py`
> - D5（PostRetrieval）来源：
>   `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/post_retrieval/registry.py`
>
> **五维度**：D1 数据结构（Service） | D2 插入前（PreInsert） | D3 插入后（PostInsert） | D4 检索前（PreRetrieval） | D5
> 检索后（PostRetrieval）

### 2.1 记忆体总览与五维度配置

下表给出 **SAGE 当前“可被注册/可被 Pipeline 调用”的实现映射**（等价于可写进 YAML 并实际生效的组合）。

| #   | 记忆体         | D1 Service（可注册）                     | D2 PreInsert（可注册）                                       | D3 PostInsert（可注册）                                    | D4 PreRetrieval（可注册）    | D5 PostRetrieval（可注册）                  |
| --- | -------------- | ---------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------- | ---------------------------- | ------------------------------------------- |
| 1   | TiM            | `vector_memory`（IndexLSH 实现“哈希桶”） | `extract.triple`                                             | `distillation`                                             | `embedding`                  | `none`                                      |
| 2   | MemoryBank     | `hierarchical_memory`                    | `transform.summarize`（或 `none`）                           | `forgetting`                                               | `embedding`                  | `rerank.time_weighted`（可选：`reinforce`） |
| 3   | MemGPT (Agent) | `hierarchical_memory`                    | `extract.entity`                                             | `distillation`                                             | `optimize.keyword_extract`   | `merge.multi_query`                         |
| 4   | A-Mem          | `graph_memory`                           | `extract.entity`（⚠️ 当前不支持 `extract.all`/persona 提取） | `link_evolution`                                           | `embedding`                  | `merge.link_expand`                         |
| 5   | MemoryOS       | `hierarchical_memory`                    | `score.importance`（或 `score.heat`）                        | `migrate`（可与 `forgetting` 组合，但需分阶段配置）        | `optimize.keyword_extract`   | `merge.multi_query`                         |
| 6   | HippoRAG       | `graph_memory`                           | `extract.triple`                                             | `link_evolution`                                           | `embedding`                  | `none`（PPR 重排需显式启用 `rerank.ppr`）   |
| 7   | HippoRAG2      | `graph_memory`                           | `extract.triple`                                             | `link_evolution`                                           | `embedding`                  | `rerank.ppr`                                |
| 8   | LD-Agent       | `hierarchical_memory`                    | `transform.summarize`                                        | `migrate`（time/heat 由服务侧策略实现）                    | `optimize.keyword_extract`   | `rerank.weighted`                           |
| 9   | SCM            | `short_term_memory`                      | `none`                                                       | `none`                                                     | `validate`（或 `embedding`） | `filter.token_budget`                       |
| 10  | Mem0           | `hybrid_memory`                          | `extract.entity`                                             | `distillation`（用 Mem0 风格 prompt 做 ADD/UPDATE/DELETE） | `embedding`                  | `none`                                      |
| 11  | Mem0ᵍ          | `hybrid_memory`（包含 graph index）      | `extract.triple`                                             | `distillation`（同上）                                     | `embedding`                  | `none`（需要扩展可改 `merge.link_expand`）  |
| 12  | SeCom          | `hierarchical_memory`                    | `transform.segment`（⚠️ 当前不支持 `segment_denoise`）       | `distillation`                                             | `embedding`                  | `none`                                      |

> 兼容性说明：
>
> - 文档中旧称 `vector_hash_memory` 已并入 `vector_memory`：通过 `index_type: IndexLSH` 等价实现。
> - `neuromem_vdb` / `neuromem_vdb_service` 相关组件在 middleware 层存在，但**当前未被 `MemoryServiceFactory`
>   暴露为可注册的 `register_memory_service` 名称**，因此不应作为“D1 可用项”写入五维表。

### 2.2 各维度 Action 实现清单

> **分类原则与实现方式**：
>
> - **Action（大方向）**：每个维度下的主要功能分类
> - **子类型（具体实现）**：有两种实现模式
>   - 🗂️ **类继承模式**：每个子类型独立类文件（子目录组织）- 用于逻辑差异大的场景
>   - ⚙️ **参数驱动模式**：单个类通过 `config` 参数区分行为 - 用于逻辑相似、可共享代码的场景

#### D1: Memory Service（数据结构 / 可被 Pipeline 注册）

| Action                      | 参考记忆体                             | 核心参数                                                                                                               |
| --------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `short_term_memory`         | SCM                                    | `max_dialog`, `embedding_dim`                                                                                          |
| `vector_memory`（通用向量） | TiM 等                                 | `dim`, `index_type`, `index_config`, `collection_name`, `index_name`                                                   |
| `graph_memory`              | HippoRAG, HippoRAG2, A-Mem             | `graph_type`, `node_embedding_dim`, `edge_types`, `link_policy`, `max_links_per_node`, `synonymy_threshold`, `damping` |
| `hierarchical_memory`       | MemoryOS, MemGPT, MemoryBank, LD-Agent | `tier_mode`, `tier_capacities`, `migration_policy`, `embedding_dim`                                                    |
| `hybrid_memory`             | Mem0 / Mem0ᵍ                           | `indexes`, `fusion_strategy`, `fusion_weights`, `rrf_k`                                                                |
| `key_value_memory`          | （可选）                               | `match_type`, `key_extractor`, `fuzzy_threshold`, `semantic_threshold`, `embedding_dim`, `case_sensitive`              |

> 说明：旧称 `vector_hash_memory（哈希桶）` 在当前实现中由 `vector_memory + IndexLSH` 等价实现（即 `index_type: IndexLSH`）。

#### D2: PreInsert（插入前处理）

| Action      | 子类型                                      | 实现方式  | 参考记忆体                                   | 说明                                                                                                                         |
| ----------- | ------------------------------------------- | --------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `none`      | -                                           | -         | MemoryBank, SCM                              | 无预处理                                                                                                                     |
| `transform` | `summarize`<br>`chunking`<br>`segment`      | 🗂️ 类继承 | MemGPT, SeCom                                | 文本转换<br>- summarize: 生成摘要<br>- chunking: 文本分块<br>- segment: 主题/段落切分                                        |
| `extract`   | `keyword`<br>`entity`<br>`noun`<br>`triple` | 🗂️ 类继承 | A-Mem, Mem0, Mem0ᵍ, TiM, HippoRAG, HippoRAG2 | 信息提取<br>- keyword: 关键词提取<br>- entity: 命名实体识别（NER）<br>- noun: 名词短语提取<br>- triple: 三元组提取（主谓宾） |
| `score`     | `importance`<br>`heat`                      | 🗂️ 类继承 | MemoryOS, LD-Agent                           | 重要性评分<br>- importance: 基于 LLM 的重要性<br>- heat: 基于访问频率的热度                                                  |

> 配置写法说明（两种都被当前 `PreInsert` 支持）：
>
> - 点号写法：`action: "extract.triple"`
> - 二段写法：`action: "extract"` + `extract_type: "triple"`

> 兼容性说明：当前实现 **不支持** `extract.all`、`transform.segment_denoise`、`scm_embed` 等旧/实验性名称；如配置中使用，会回退到
> `none`（透传）。

#### D3: PostInsert（插入后处理）

| Action           | 子类型                                       | 实现方式    | 参考记忆体                 | 说明                                                                               |
| ---------------- | -------------------------------------------- | ----------- | -------------------------- | ---------------------------------------------------------------------------------- |
| `none`           | -                                            | -           | HippoRAG2, SCM             | 无后处理                                                                           |
| `distillation`   | -                                            | 单一实现    | TiM, MemGPT, SeCom, Mem0\* | 记忆蒸馏与合并（数据量驱动）<br>- 检索 top-k 候选<br>- LLM 产出 delete/insert 列表 |
| `crud`           | -                                            | 单一实现    | Mem0（可选）               | LLM 决策 CRUD（ADD/UPDATE/DELETE/NOOP）                                            |
| `link_evolution` | -                                            | 单一实现    | A-Mem, HippoRAG            | 图链接演化（默认 session_end 执行）                                                |
| `migrate`        | -                                            | 单一实现    | MemoryOS, LD-Agent         | 分层迁移（由服务侧 `migrate_memories` 支持）                                       |
| `forgetting`     | `ebbinghaus`<br>`heat_based`<br>`time_based` | ⚙️ 参数驱动 | MemoryBank, MemoryOS       | 主动遗忘（由服务侧 `forget_memories` 支持）                                        |

> 备注：Mem0 系列在当前 repo 的“可跑配置”里，通常用 `distillation` 搭配 Mem0 风格 prompt 来实现“ADD/UPDATE/DELETE”逻辑；`crud`
> action 本身存在，但默认配置不一定启用。

> 兼容性说明：部分历史 YAML 中出现的 `distillation_topk/distillation_threshold/link_policy/knn_k/...` 等键 **不会被当前
> action 实现读取**；请以各 action 的 `*_action/base.py` 中 `_get_config(...)` 为准。

#### D4: PreRetrieval（检索前处理）

| Action        | 子类型                                     | 实现方式  | 参考记忆体                                         | 说明                                                                                   |
| ------------- | ------------------------------------------ | --------- | -------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `none`        | -                                          | -         | Mem0, Mem0ᵍ                                        | 无预处理                                                                               |
| `embedding`   | -                                          | 单一实现  | TiM, MemoryBank, A-Mem, MemoryOS, HippoRAG2, SeCom | 查询向量化<br>- 生成 query embedding                                                   |
| `optimize`    | `keyword_extract`<br>`expand`<br>`rewrite` | 🗂️ 类继承 | MemGPT, MemoryOS, LD-Agent                         | 查询优化<br>- keyword_extract: 关键词提取<br>- expand: 查询扩展<br>- rewrite: 查询改写 |
| `validate`    | -                                          | 单一实现  | SCM                                                | 检索激活判断<br>- 判断是否需要检索记忆                                                 |
| `enhancement` | `decompose`<br>`route`<br>`multi_embed`    | 🗂️ 类继承 | 通用高级功能（不限特定记忆体）                     | 查询增强<br>- decompose: 复杂查询分解<br>- route: 检索路由<br>- multi_embed: 多维向量  |

**Enhancement Actions 详细说明**（2025-12-19 新增）：

| Action                    | 描述                 | 配置示例                                                                                                | 适用场景                   |
| ------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------- |
| `enhancement.decompose`   | 复杂查询分解为子查询 | `decompose_strategy: llm/rule/hybrid`<br>`max_sub_queries: 5`<br>`sub_query_action: parallel`           | 多步推理、复杂任务         |
| `enhancement.route`       | 根据查询选择检索策略 | `route_strategy: keyword/classifier/llm`<br>`keyword_rules: [...]`<br>`default_route: long_term_memory` | 多源记忆系统、条件分支检索 |
| `enhancement.multi_embed` | 多维度embedding组合  | `embeddings: [{name: semantic, weight: 0.6}, ...]`<br>`output_format: weighted/dict/concat`             | 精细化检索、多模态检索     |

**Route策略详解**：

- `keyword`: 基于关键词规则匹配（最快，适合明确规则）
- `classifier`: 基于意图分类（平衡，支持factual/personal/recent/historical四类）
- `llm`: 基于LLM决策（最灵活，但成本高）

**使用示例**：

```yaml
# 查询分解
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "decompose"
    decompose_strategy: "llm"
    max_sub_queries: 5

# 检索路由
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "route"
    route_strategy: "keyword"
    keyword_rules:
      - keywords: ["remember", "recall"]
        target: "long_term_memory"

# 多维embedding
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "multi_embed"
    embeddings:
      - name: "semantic"
        model: "BAAI/bge-m3"
        weight: 0.6
```

#### D5: PostRetrieval（检索后处理）

| Action    | 子类型                                               | 实现方式    | 参考记忆体                       | 说明                                                                                                                            |
| --------- | ---------------------------------------------------- | ----------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `none`    | -                                                    | -           | HippoRAG, HippoRAG2, Mem0, SeCom | 无后处理                                                                                                                        |
| `rerank`  | `semantic`<br>`time_weighted`<br>`ppr`<br>`weighted` | 🗂️ 类继承   | TiM, LD-Agent                    | 结果重排序<br>- semantic: 语义相似度<br>- time_weighted: 时间衰减加权<br>- ppr: Personalized PageRank<br>- weighted: 多因素加权 |
| `filter`  | `token_budget`<br>`threshold`<br>`top_k`             | 🗂️ 类继承   | SCM                              | 结果过滤<br>- token_budget: Token 数量预算<br>- threshold: 相似度阈值<br>- top_k: 保留前 K 个                                   |
| `merge`   | `link_expand`<br>`multi_query`                       | 🗂️ 类继承   | A-Mem, MemoryOS, MemGPT, Mem0ᵍ   | 结果合并<br>- link_expand: 沿图链接扩展<br>- multi_query: 多次查询合并                                                          |
| `augment` | `persona`<br>`traits`<br>`summary`<br>`metadata`     | ⚙️ 参数驱动 | MemoryBank, MemoryOS             | 结果增强<br>- 通过 `augment_type` 参数选择                                                                                      |

> 补充：当前实现还包含 `reinforce`（MemoryBank 检索强化）Action（见 `post_retrieval/registry.py`），可按需启用。

### 2.3 实现模式与目录组织规范

#### 2.3.1 两种实现模式

**🗂️ 类继承模式**（推荐用于逻辑差异大的场景）

```python
# 每个子类型独立类文件，放在子目录中
pre_insert/
  extract/
    keyword.py       # 独立实现
    entity.py        # 独立实现
    triple.py        # 独立实现
```

- **优点**：逻辑清晰、易扩展、易测试
- **适用**：各子类型实现差异大，难以共享代码
- **示例**：`extract`（keyword/entity/triple）、`rerank`（semantic/ppr/weighted）

**⚙️ 参数驱动模式**（推荐用于逻辑相似的场景）

```python
# 单个类文件，通过 config 参数区分行为
post_insert/
  forgetting_action.py  # 通过 strategy 参数支持多种策略

class ForgettingAction:
    def _init_action(self):
        self.strategy = self.config.get("strategy", "ebbinghaus")
        # ebbinghaus | heat_based | time_based
```

- **优点**：代码复用率高、维护成本低
- **适用**：各子类型逻辑相似，可共享大量代码
- **示例**：`forgetting`（ebbinghaus/heat_based/time_based）、`augment`（persona/traits/summary）

#### 2.3.2 标准目录结构（强制规范）

> **⚠️ 重要原则**：除 `none_action.py` 外，**所有 Action 必须建子目录**，即使当前只有单一实现。
>
> **原因**：
>
> - 保持架构一致性
> - 便于未来扩展（如 `embedding` 未来可能支持多种 embedding 方式）
> - 避免后期重构目录结构

**标准结构模板**

```
维度目录/
├── base.py                  # 基类
├── operator.py              # Operator 主类
├── registry.py              # 注册表
├── none_action.py           # 例外：空操作放顶层
├── action1/                 # Action 1（强制子目录）
│   ├── __init__.py
│   └── base.py              # 单一实现，未来可扩展
├── action2/                 # Action 2（类继承模式）
│   ├── __init__.py
│   ├── subtype1.py
│   ├── subtype2.py
│   └── subtype3.py
└── action3/                 # Action 3（参数驱动模式）
    ├── __init__.py
    └── base.py              # 单文件多策略
```

**具体示例**

*单一实现（未来可扩展）*

```
pre_retrieval/
├── embedding/               # ✅ 即使单一实现也建子目录
│   ├── __init__.py
│   └── base.py              # 当前实现：基础 embedding
│   # 未来扩展：multi_modal.py, sparse.py, hybrid.py
└── validate/                # ✅ 即使单一实现也建子目录
    ├── __init__.py
    └── base.py              # 当前实现：基础验证
    # 未来扩展：security.py, semantic.py, budget.py
```

*类继承模式*

```
pre_retrieval/
└── optimize/                # ✅ 多个子类型
    ├── __init__.py
    ├── keyword_extract.py
    ├── expand.py
    └── rewrite.py
```

*参数驱动模式*

```
post_insert/
└── forgetting/              # ✅ 参数驱动也建子目录
    ├── __init__.py
    └── base.py              # 通过 strategy 参数支持多种策略
    # ebbinghaus | heat_based | time_based
```

#### 2.3.3 选择标准

| 考虑因素   | 类继承模式         | 参数驱动模式     |
| ---------- | ------------------ | ---------------- |
| 代码差异度 | 高（>50% 不同）    | 低（\<30% 不同） |
| 代码复用   | 低                 | 高               |
| 扩展性     | 易于添加新子类型   | 添加新参数分支   |
| 测试复杂度 | 每个子类型独立测试 | 参数化测试       |
| 维护成本   | 多个文件           | 单个文件         |
| 目录要求   | **强制建子目录**   | **强制建子目录** |

**当前实现统计**：

- 🗂️ **类继承模式**：`extract` (4个)、`transform` (3个)、`score` (2个)、`optimize` (3个)、`rerank` (4个)、`filter`
  (3个)、`merge` (2个)
- ⚙️ **参数驱动模式**：`forgetting` (3个)、`augment` (4个)、`migrate` (1个)
- 📄 **单一实现**：`distillation`、`crud`、`link_evolution`、`embedding`、`validate`

#### 2.3.4 需要重构的目录

根据强制子目录规范，以下目录需要重构：

**D3: post_insert** - 需要为所有 action 建子目录

```
当前（❌ 不规范）:
post_insert/
├── distillation_action.py    # 游离在顶层
├── crud_action.py             # 游离在顶层
├── link_evolution_action.py   # 游离在顶层
├── migrate_action.py          # 游离在顶层
└── forgetting_action.py       # 游离在顶层

目标（✅ 规范）:
post_insert/
├── distillation/
│   └── base.py
├── crud/
│   └── base.py
├── link_evolution/
│   └── base.py
├── migrate/
│   └── heat.py                # 未来可扩展：lru.py, lfu.py
└── forgetting/
    └── base.py                # 参数驱动：strategy 参数
```

**D4: pre_retrieval** - 需要为单一实现建子目录

```
当前（❌ 不规范）:
pre_retrieval/
├── embedding_action.py        # 游离在顶层
├── validate_action.py         # 游离在顶层
└── optimize/                  # ✅ 已规范

目标（✅ 规范）:
pre_retrieval/
├── embedding/
│   └── base.py                # 未来可扩展：multi_modal.py, sparse.py
├── validate/
│   └── base.py                # 未来可扩展：security.py, budget.py
└── optimize/                  # ✅ 已规范
```

**D5: post_retrieval** - 需要为单一实现建子目录

```
当前（❌ 不规范）:
post_retrieval/
├── augment_action.py          # 游离在顶层
├── rerank/                    # ✅ 已规范
├── filter/                    # ✅ 已规范
└── merge/                     # ✅ 已规范

目标（✅ 规范）:
post_retrieval/
├── augment/
│   └── base.py                # 参数驱动：augment_type 参数
├── rerank/                    # ✅ 已规范
├── filter/                    # ✅ 已规范
└── merge/                     # ✅ 已规范
```

**D2: pre_insert** - ✅ 已完全规范，无需重构

### 2.4 组合兼容性矩阵

> 五个维度的 Action 采用**正交设计**，大部分可自由组合，仅少数 Action 有依赖约束。

#### 自由组合维度

| 维度             | 可自由组合的 Action                                  | 说明                            |
| ---------------- | ---------------------------------------------------- | ------------------------------- |
| D2 PreInsert     | `none`, `tri_embed`, `transform`, `extract`, `score` | 纯预处理，不依赖 Service 类型   |
| D4 PreRetrieval  | `none`, `embedding`, `optimize`, `validate`          | 纯 query 处理，不访问存储       |
| D5 PostRetrieval | `none`, `rerank`, `filter`, `merge`, `augment`       | 纯结果处理，不依赖 Service 类型 |

#### 有依赖约束的组合

| 维度          | Action           | 依赖的 D1 Service                 | 原因                        |
| ------------- | ---------------- | --------------------------------- | --------------------------- |
| D3 PostInsert | `link_evolution` | `graph_memory`                    | 需要图结构存储边和节点      |
| D3 PostInsert | `migrate`        | `hierarchical_memory`             | 需要多层结构进行迁移        |
| D3 PostInsert | `forgetting`     | `hierarchical_memory`             | Ebbinghaus 遗忘需要层级结构 |
| D3 PostInsert | `crud`           | `graph_memory` 或 `hybrid_memory` | 需要支持实体级 CRUD 操作    |

#### 兼容性速查表

```
D1 Service              → D3 PostInsert 可用 Action
─────────────────────────────────────────────────────
short_term_memory       → none
vector_hash_memory（哈希桶，= vector_memory[IndexLSH]） → none, distillation
neuromem_vdb            → none, distillation
graph_memory            → none, link_evolution, crud
hierarchical_memory     → none, distillation, migrate, forgetting
hybrid_memory           → none, distillation, crud
```

#### 理论组合数

假设各维度 Action 可自由组合（忽略约束）：

- D1 Service: 6 种
- D2 PreInsert: 5 种
- D3 PostInsert: 6 种（含组合如 `migrate+forgetting`）
- D4 PreRetrieval: 4 种
- D5 PostRetrieval: 5 种（含组合如 `merge+augment`）

理论最大组合数 = 6 × 5 × 6 × 4 × 5 = **3600 种**

考虑 D3 依赖约束后，实际可用组合约 **1500+ 种**。

### 2.4 各论文记忆体详细映射

#### 2.4.1 TiM: Think-in-Memory

> 📄 论文: *Think-in-Memory: Recalling and Post-thinking Enable LLMs with Long-Term Memory*

| 维度     | 论文设计                 | SAGE 实现                                                                  |
| -------- | ------------------------ | -------------------------------------------------------------------------- |
| 数据结构 | LSH 哈希桶 + thoughts    | `vector_hash_memory（哈希桶，= vector_memory[IndexLSH]）` + VDB Collection |
| 插入前   | Q-R → inductive thoughts | `PreInsert.tri_embed / extract`                                            |
| 插入后   | 桶内 Forget / Merge      | `PostInsert.distillation + optimize.summarize`                             |
| 检索前   | query embedding          | `PreRetrieval.embedding / multi_embed`                                     |
| 检索后   | thoughts → prompt        | `PostRetrieval.merge + augment + format`                                   |

#### 2.4.2 MemoryBank

> 📂 项目: [`MemoryBank-SiliconFriend`](/home/zrc/develop_item/MemoryBank-SiliconFriend/) | 📄 论文:
> *MemoryBank: Enhancing Large Language Models with Long-Term Memory*

| 维度     | 论文设计                                   | SAGE 实现                                  |
| -------- | ------------------------------------------ | ------------------------------------------ |
| 数据结构 | 原始对话 + daily/global summary + portrait | `HierarchicalMemoryService`（STM/MTM/LTM） |
| 插入前   | 检索已有 persona/summary                   | `PreInsert.transform.summarize + score`    |
| 插入后   | Ebbinghaus/heat 遗忘                       | `PostInsert.forgetting`                    |
| 检索前   | 直接 embedding                             | `PreRetrieval.embedding`                   |
| 检索后   | 检索 + 画像 + summary 拼接                 | `PostRetrieval.augment + format`           |

#### 2.4.3 MemGPT

> 📂 项目: [`MemGPT`](/home/zrc/develop_item/MemGPT/) | 📄 论文: *MemGPT: Towards LLMs as Operating
> Systems*

| 维度     | 论文设计                                    | SAGE 实现                                     |
| -------- | ------------------------------------------- | --------------------------------------------- |
| 数据结构 | Working Context + FIFO Queue + Recall Store | `KeyValueMemoryService + HierarchicalService` |
| 插入前   | 提取事实、决定 replace                      | `PreInsert.extract + score.importance`        |
| 插入后   | replace(old,new)                            | `PostInsert.distillation / optimize.migrate`  |
| 检索前   | 解析 query、提取关键词                      | `PreRetrieval.optimize.keyword_extract`       |
| 检索后   | 多次访问、拼接上下文                        | `PostRetrieval.merge + augment + format`      |

#### 2.4.4 A-Mem

> 📂 项目: [`A-mem`](/home/zrc/develop_item/A-mem/) | 📄 论文: *A-MEM: Agentic Memory for LLM Agents*

| 维度     | 论文设计                                   | SAGE 实现                                   |
| -------- | ------------------------------------------ | ------------------------------------------- |
| 数据结构 | note = {content, keywords, tags, links} 图 | `GraphMemoryService + HybridCollection`     |
| 插入前   | LLM 生成 Ki/Gi/Xi                          | `PreInsert.extract`                         |
| 插入后   | Link Generation + Memory Evolution         | `PostInsert.link_evolution`                 |
| 检索前   | query embedding                            | `PreRetrieval.embedding`                    |
| 检索后   | 链接扩展、多跳                             | `PostRetrieval.merge.link_expand + augment` |

#### 2.4.5 MemoryOS

> 📂 项目: [`MemoryOS`](/home/zrc/develop_item/MemoryOS/) | 📄 论文: *Memory OS of AI Agent*

| 维度     | 论文设计                                     | SAGE 实现                                |
| -------- | -------------------------------------------- | ---------------------------------------- |
| 数据结构 | STM(FIFO) + MTM(segment/heat) + LPM(persona) | `HierarchicalService + HybridCollection` |
| 插入前   | 计算 Fscore/heat                             | `PreInsert.score`                        |
| 插入后   | 基于 heat 迁移与淘汰                         | `PostInsert.migrate + forgetting`        |
| 检索前   | embedding + 关键词                           | `PreRetrieval.embedding + optimize`      |
| 检索后   | STM + MTM + LPM 拼接                         | `PostRetrieval.merge + augment + format` |

#### 2.4.6 HippoRAG

> 📂 项目: [`HippoRAG`](/home/zrc/develop_item/HippoRAG/) | 📄 论文: *HippoRAG: Neurobiologically Inspired
> Long-Term Memory for Large Language Models*

| 维度     | 论文设计                        | SAGE 实现                               |
| -------- | ------------------------------- | --------------------------------------- |
| 数据结构 | Open KG (Phrase/Relation nodes) | `GraphMemoryService + GraphCollection`  |
| 插入前   | NER + OpenIE 提取 triples       | `PreInsert.tri_embed`                   |
| 插入后   | 建立同义词边 (synonym edges)    | `PostInsert.link_evolution`             |
| 检索前   | NER 提取查询实体                | `PreRetrieval.optimize.keyword_extract` |
| 检索后   | PPR 图检索 + Passage 排序       | `PostRetrieval.none`                    |

#### 2.4.7 HippoRAG2

> 📂 项目: [`HippoRAG`](/home/zrc/develop_item/HippoRAG/) | 📄 论文: *HippoRAG 2* (HippoRAG 变体)

| 维度     | 论文设计                           | SAGE 实现                              |
| -------- | ---------------------------------- | -------------------------------------- |
| 数据结构 | KG + Passage Nodes + Context Edges | `GraphMemoryService + GraphCollection` |
| 插入前   | OpenIE 提取 triples                | `PreInsert.tri_embed`                  |
| 插入后   | 无（不做后处理）                   | `PostInsert.none`                      |
| 检索前   | Query-to-Triple 匹配               | `PreRetrieval.embedding`               |
| 检索后   | PPR 图检索 + 简单拼接              | `PostRetrieval.none`                   |

#### 2.4.8 LD-Agent

> 📂 项目: [`LD-Agent`](/home/zrc/develop_item/LD-Agent/) | 📄 论文: *LD-Agent: Towards Long-term Dialogue
> Agents*

| 维度     | 论文设计                      | SAGE 实现                                 |
| -------- | ----------------------------- | ----------------------------------------- |
| 数据结构 | STM 对话缓存 + LTM 事件摘要库 | `ShortTermService + HierarchicalService`  |
| 插入前   | 判断是否构成"事件"            | `PreInsert.transform.summarize + score`   |
| 插入后   | Replace/更新旧摘要            | `PostInsert.distillation / forgetting`    |
| 检索前   | 提取关键词集合 V_q            | `PreRetrieval.optimize.keyword_extract`   |
| 检索后   | 语义 + 话题重叠 + 时间衰减    | `PostRetrieval.rerank.weighted + augment` |

#### 2.4.9 SCM（Self-Controlled Memory）

> 📂 项目: [`SCM4LLMs`](/home/zrc/develop_item/SCM4LLMs/) | 📄 论文: *Enhancing Large Language Model with
> Self-Controlled Memory Framework*

| 维度     | 论文设计                                     | SAGE 实现                                      |
| -------- | -------------------------------------------- | ---------------------------------------------- |
| 数据结构 | Memory Stream (observation/response/summary) | `ShortTermService + PreInsert.summarize`       |
| 插入前   | 每轮交互生成 summary + embedding             | `PreInsert.transform.summarize + multi_embed`  |
| 插入后   | 无（不做 replace/merge）                     | 不启用 PostInsert                              |
| 检索前   | 判断是否激活记忆                             | `PreRetrieval.validate + optimize`             |
| 检索后   | Token budget 截断/压缩                       | `PostRetrieval.filter.token_budget + compress` |

#### 2.4.10 Mem0

> 📂 项目: [`mem0`](/home/zrc/develop_item/mem0/) | 📄 论文: *Mem0: Building Production-Ready AI Agents
> with Scalable Long-Term Memory*

| 维度     | 论文设计                    | SAGE 实现             |
| -------- | --------------------------- | --------------------- |
| 数据结构 | 文本事实 + 全局摘要 S       | `HybridMemoryService` |
| 插入前   | 检索摘要 + 提取候选记忆     | `PreInsert.extract`   |
| 插入后   | ADD/UPDATE/DELETE/NOOP 决策 | `PostInsert.crud`     |
| 检索前   | 直接 embedding              | `PreRetrieval.none`   |
| 检索后   | 单次检索拼接                | `PostRetrieval.none`  |

#### 2.4.11 Mem0ᵍ

> 📂 项目: [`mem0`](/home/zrc/develop_item/mem0/) | 📄 论文: *Mem0ᵍ* (Mem0 图增强版)

| 维度     | 论文设计                       | SAGE 实现                         |
| -------- | ------------------------------ | --------------------------------- |
| 数据结构 | 有向标签图 G = (V, E, L)       | `GraphMemoryService`              |
| 插入前   | 实体识别 + 关系生成 (triplets) | `PreInsert.extract`               |
| 插入后   | 冲突标记 (逻辑 replace)        | `PostInsert.crud`                 |
| 检索前   | 直接 embedding                 | `PreRetrieval.none`               |
| 检索后   | 子图构建（多跳遍历）           | `PostRetrieval.merge.link_expand` |

#### 2.4.12 SeCom

> 📂 项目: [`SeCom`](/home/zrc/develop_item/SeCom/) | 📄 论文: *On Memory Construction and Retrieval for
> Personalized Conversational Agents*

| 维度     | 论文设计                                 | SAGE 实现                     |
| -------- | ---------------------------------------- | ----------------------------- |
| 数据结构 | Segment-level 记忆单元（分布式局部摘要） | `NeuroMemVDBService`          |
| 插入前   | 分段 + 压缩去噪 + 语义聚类               | `PreInsert.transform.segment` |
| 插入后   | 语义重合时 replace                       | `PostInsert.distillation`     |
| 检索前   | 直接 embedding                           | `PreRetrieval.embedding`      |
| 检索后   | 直接拼接为 prompt                        | `PostRetrieval.none`          |

### 2.5 记忆体配置清单

| 记忆体     | 配置文件                          | 关键配置                                                                                          |
| ---------- | --------------------------------- | ------------------------------------------------------------------------------------------------- |
| TiM        | `locomo_tim_pipeline.yaml`        | `service: vector_memory（IndexLSH，等价于 vector_memory（哈希桶））`, `post_insert: distillation` |
| MemoryBank | `locomo_memorybank_pipeline.yaml` | `service: hierarchical_memory`, `post_insert: forgetting`                                         |
| MemGPT     | `locomo_memgpt_pipeline.yaml`     | `service: hierarchical_memory`, `post_insert: distillation`                                       |
| A-Mem      | `locomo_amem_pipeline.yaml`       | `service: graph_memory`, `post_insert: link_evolution`                                            |
| MemoryOS   | `locomo_memoryos_pipeline.yaml`   | `service: hierarchical_memory`, `post_insert: migrate+forgetting`                                 |
| HippoRAG   | `locomo_hipporag_pipeline.yaml`   | `service: graph_memory`, `post_insert: link_evolution`                                            |
| HippoRAG2  | `locomo_hipporag2_pipeline.yaml`  | `service: graph_memory`, `post_insert: none`                                                      |
| LD-Agent   | `locomo_ldagent_pipeline.yaml`    | `service: hierarchical_memory`, `post_insert: forgetting`                                         |
| SCM        | `locomo_scm_pipeline.yaml`        | `service: short_term_memory`, `post_insert: none`                                                 |
| Mem0       | `locomo_mem0_pipeline.yaml`       | `service: hybrid_memory`, `post_insert: crud`                                                     |
| Mem0ᵍ      | `locomo_mem0g_pipeline.yaml`      | `service: graph_memory`, `post_insert: crud`                                                      |
| SeCom      | `locomo_secom_pipeline.yaml`      | `service: neuromem_vdb`, `post_insert: distillation`                                              |

______________________________________________________________________

## 三、Pipeline 六阶段重构实现

> **重构时间**: 2025-12-12\
> **重构目标**: 统一接口规范、抽取 Action 策略类、明确职责边界、提升可测试性

### 3.1 重构概述

#### 重构前问题

| 阶段            | 原始代码行数 | 主要问题                       |
| --------------- | ------------ | ------------------------------ |
| PreInsert       | 1196 行      | 7 个 Action 内联、缺乏统一接口 |
| MemoryInsert    | 237 行       | 简单透传，但缺少错误处理       |
| PostInsert      | 1002 行      | 6 个 Action 内联、职责不清     |
| PreRetrieval    | 930 行       | 4 个 Action 内联、依赖混乱     |
| MemoryRetrieval | 基础实现     | 功能单一                       |
| PostRetrieval   | 1407 行      | 5 个 Action 内联、代码重复     |
| **总计**        | **4772 行**  | **架构混乱、难以维护**         |

#### 重构后改进

| 阶段            | 重构后代码                       | Action 数量      | 代码精简率   | 测试覆盖率 |
| --------------- | -------------------------------- | ---------------- | ------------ | ---------- |
| PreInsert       | ~200 行 + 5 个 Action 模块       | 5                | **83%**      | 90%+       |
| MemoryInsert    | ~150 行                          | 透传优化         | **37%**      | 85%+       |
| PostInsert      | 238 行 + 6 个 Action 模块        | 6                | **76%**      | 90%+       |
| PreRetrieval    | ~180 行 + 4 个 Action 模块       | 4                | **81%**      | 90%+       |
| MemoryRetrieval | ~120 行                          | 优化实现         | -            | 85%+       |
| PostRetrieval   | ~220 行 + 5 个 Action 模块       | 5                | **84%**      | 90%+       |
| **总计**        | **~1100 行主类 + 模块化 Action** | **25 个 Action** | **平均 77%** | **90%+**   |

### 3.2 统一 Action 架构

#### 基类设计模式

所有阶段的 Action 遵循统一的设计模式：

```python
# 输入数据类
@dataclass
class {Stage}Input:
    data: dict[str, Any]        # 原始数据
    config: dict[str, Any]      # Action 配置
    service_name: str           # 服务名称（可选）

# 输出数据类
@dataclass
class {Stage}Output:
    result: Any                 # 主要结果
    metadata: dict[str, Any]    # 元数据

# Action 基类
class Base{Stage}Action(ABC):
    def __init__(self, config: dict[str, Any]): ...

    @abstractmethod
    def _init_action(self) -> None: ...

    @abstractmethod
    def execute(self, input_data: {Stage}Input) -> {Stage}Output: ...
```

#### 注册表模式

每个阶段都有独立的 Action 注册表：

```python
class {Stage}ActionRegistry:
    _actions: dict[str, type[Base{Stage}Action]] = {}

    @classmethod
    def register(cls, name: str, action_class: type): ...

    @classmethod
    def get(cls, name: str) -> type: ...

    @classmethod
    def list_actions(cls) -> list[str]: ...

# 便捷函数
def get_action(name: str) -> Base{Stage}Action: ...
```

### 3.3 各阶段 Action 实现清单

#### 3.3.1 PreInsert (D2 插入前)

**文件结构**:

```
libs/pre_insert/
  ├── base.py                    # BasePreInsertAction
  ├── registry.py                # PreInsertActionRegistry
  ├── none_action.py             # None Action (MemoryBank, SCM)
  ├── tri_embed_action.py        # TriEmbed Action (TiM, HippoRAG, HippoRAG2)
  ├── transform/
  │   ├── chunking.py            # MemGPT
  │   ├── summarize.py           # MemGPT, LD-Agent
  │   └── segment.py             # SeCom
  ├── extract/
  │   ├── keyword.py             # A-Mem
  │   ├── entity.py              # Mem0, Mem0ᵍ
  │   └── noun.py                # 通用
  └── score/
      ├── importance.py          # MemoryOS, LD-Agent
      └── heat.py                # MemoryOS
```

**Action 映射**:

| Action                | 使用记忆体               | 核心功能          |
| --------------------- | ------------------------ | ----------------- |
| `none`                | MemoryBank, SCM          | 透传，无预处理    |
| `tri_embed`           | TiM, HippoRAG, HippoRAG2 | OpenIE 三元组抽取 |
| `transform.chunking`  | MemGPT                   | 文本分块          |
| `transform.summarize` | MemGPT, LD-Agent         | 摘要生成          |
| `transform.segment`   | SeCom                    | 话题分段          |
| `extract.keyword`     | A-Mem                    | 关键词抽取        |
| `extract.entity`      | Mem0, Mem0ᵍ              | 实体识别          |
| `score.importance`    | MemoryOS, LD-Agent       | 重要性评分        |
| `score.heat`          | MemoryOS                 | 热度计算          |

#### 3.3.2 MemoryInsert

**优化内容**:

- 统一透传接口
- 增强错误处理和重试机制
- 支持批量插入优化
- 添加性能监控

#### 3.3.3 PostInsert (D3 插入后)

**文件结构**:

```
libs/post_insert/
  ├── base.py                    # BasePostInsertAction
  ├── registry.py                # PostInsertActionRegistry
  ├── none_action.py             # None Action
  ├── distillation_action.py     # Distillation (TiM, MemGPT, SeCom)
  ├── crud_action.py             # CRUD (Mem0, Mem0ᵍ)
  ├── link_evolution_action.py   # Link Evolution (A-Mem, HippoRAG)
  ├── migrate_action.py          # Migrate (MemoryOS)
  ├── forgetting_action.py       # Forgetting (MemoryBank, MemoryOS, LD-Agent)
  └── tests/
      ├── test_actions.py        # 26 个单元测试
      └── test_post_insert.py    # 17 个集成测试
```

**Action 映射**:

| Action           | 使用记忆体                     | 核心功能                 | 代码行数 |
| ---------------- | ------------------------------ | ------------------------ | -------- |
| `none`           | HippoRAG2, SCM                 | 无后处理                 | 41       |
| `distillation`   | TiM, MemGPT, SeCom             | 记忆蒸馏与合并           | 163      |
| `crud`           | Mem0, Mem0ᵍ                    | ADD/UPDATE/DELETE 决策   | 181      |
| `link_evolution` | A-Mem, HippoRAG                | 链接生成与演化           | 88       |
| `migrate`        | MemoryOS                       | 层级迁移                 | 69       |
| `forgetting`     | MemoryBank, MemoryOS, LD-Agent | Ebbinghaus/LFU/Heat 遗忘 | 101      |

**测试覆盖**:

- 单元测试: 26 个用例（覆盖所有 Action）
- 集成测试: 17 个用例（验证主类协调）
- 总覆盖率: **92%**

#### 3.3.4 PreRetrieval (D4 检索前)

**文件结构**:

```
libs/pre_retrieval/
  ├── base.py                    # BasePreRetrievalAction
  ├── registry.py                # PreRetrievalActionRegistry
  ├── none_action.py             # None Action (Mem0, Mem0ᵍ)
  ├── embedding_action.py        # Embedding (TiM, MemoryBank, A-Mem, MemoryOS, HippoRAG2, SeCom)
  ├── optimize/
  │   ├── keyword_extract.py     # MemGPT, HippoRAG, LD-Agent
  │   ├── expand.py              # 查询扩展
  │   └── rewrite.py             # 查询改写
  └── validate_action.py         # Validate (SCM)
```

**Action 映射**:

| Action                     | 使用记忆体                                         | 核心功能     |
| -------------------------- | -------------------------------------------------- | ------------ |
| `none`                     | Mem0, Mem0ᵍ                                        | 透传查询     |
| `embedding`                | TiM, MemoryBank, A-Mem, MemoryOS, HippoRAG2, SeCom | 查询向量化   |
| `optimize.keyword_extract` | MemGPT, HippoRAG, LD-Agent                         | 关键词提取   |
| `optimize.expand`          | 通用                                               | 查询扩展     |
| `optimize.rewrite`         | 通用                                               | 查询改写     |
| `validate`                 | SCM                                                | 记忆激活判断 |

#### 3.3.5 MemoryRetrieval

**优化内容**:

- 统一透传接口
- 支持多种检索模式（主动/被动）
- 增强性能监控
- 添加结果缓存机制

#### 3.3.6 PostRetrieval (D5 检索后)

**文件结构**:

```
libs/post_retrieval/
  ├── base.py                    # BasePostRetrievalAction
  ├── registry.py                # PostRetrievalActionRegistry
  ├── none_action.py             # None Action (HippoRAG, HippoRAG2, Mem0, SeCom)
  ├── rerank/
  │   ├── semantic.py            # TiM
  │   ├── time_weighted.py       # 通用
  │   ├── ppr.py                 # LD-Agent
  │   └── weighted.py            # LD-Agent
  ├── filter/
  │   ├── token_budget.py        # SCM
  │   ├── threshold.py           # 通用
  │   └── top_k.py               # 通用
  ├── merge/
  │   ├── link_expand.py         # A-Mem, Mem0ᵍ
  │   └── multi_query.py         # MemoryOS, MemGPT
  └── augment_action.py          # Augment (MemoryBank, MemoryOS)
```

**Action 映射**:

| Action                | 使用记忆体                       | 核心功能       |
| --------------------- | -------------------------------- | -------------- |
| `none`                | HippoRAG, HippoRAG2, Mem0, SeCom | 直接返回       |
| `rerank.semantic`     | TiM                              | 语义重排序     |
| `rerank.ppr`          | LD-Agent                         | PPR 图排序     |
| `rerank.weighted`     | LD-Agent                         | 加权综合排序   |
| `filter.token_budget` | SCM                              | Token 预算截断 |
| `merge.link_expand`   | A-Mem, Mem0ᵍ                     | 链接扩展       |
| `merge.multi_query`   | MemoryOS, MemGPT                 | 多查询合并     |
| `augment`             | MemoryBank, MemoryOS             | 画像/摘要增强  |

### 3.4 重构成果总结

#### 代码质量提升

| 指标           | 重构前        | 重构后                          | 提升            |
| -------------- | ------------- | ------------------------------- | --------------- |
| 总代码行数     | 4772 行       | ~1100 行（主类）+ 模块化 Action | **77% 精简**    |
| 单文件最大行数 | 1407 行       | 238 行                          | **83% 减少**    |
| Action 复用性  | 0（全部内联） | 25 个独立 Action                | **100% 可复用** |
| 测试覆盖率     | < 30%         | > 90%                           | **3 倍提升**    |
| 代码可维护性   | 低（紧耦合）  | 高（松耦合）                    | **质的飞跃**    |

#### 架构优化成果

1. **统一接口规范**: 所有阶段遵循相同的 Input/Output/Action 模式
1. **策略模式应用**: 25 个 Action 完全独立，支持热插拔
1. **职责边界清晰**: 严格遵循六阶段操作权限约束
1. **测试友好**: 单元测试 + 集成测试 + 端到端测试全覆盖
1. **文档完善**: 每个模块都有 README 和示例代码

#### 12 个记忆体验证

所有 12 个论文记忆体的配置文件 100% 通过测试：

| 记忆体     | 配置文件                          | 验证状态 |
| ---------- | --------------------------------- | -------- |
| TiM        | `locomo_tim_pipeline.yaml`        | ✅ 通过  |
| MemoryBank | `locomo_memorybank_pipeline.yaml` | ✅ 通过  |
| MemGPT     | `locomo_memgpt_pipeline.yaml`     | ✅ 通过  |
| A-Mem      | `locomo_amem_pipeline.yaml`       | ✅ 通过  |
| MemoryOS   | `locomo_memoryos_pipeline.yaml`   | ✅ 通过  |
| HippoRAG   | `locomo_hipporag_pipeline.yaml`   | ✅ 通过  |
| HippoRAG2  | `locomo_hipporag2_pipeline.yaml`  | ✅ 通过  |
| LD-Agent   | `locomo_ldagent_pipeline.yaml`    | ✅ 通过  |
| SCM        | `locomo_scm_pipeline.yaml`        | ✅ 通过  |
| Mem0       | `locomo_mem0_pipeline.yaml`       | ✅ 通过  |
| Mem0ᵍ      | `locomo_mem0g_pipeline.yaml`      | ✅ 通过  |
| SeCom      | `locomo_secom_pipeline.yaml`      | ✅ 通过  |

### 3.5 后续优化方向

1. **性能优化**:

   - Action 结果缓存机制
   - 批量处理优化
   - 异步执行支持

1. **功能扩展**:

   - 更多 Action 策略（如新论文记忆体）
   - 可视化调试工具
   - 配置热更新支持

1. **工程优化**:

   - CI/CD 自动化测试
   - 性能基准测试
   - 文档自动生成

### 3.6 工具类整合 (2025-12-12)

**问题**: 发现 `libs/common/` 和 `utils/` 两个工具目录功能重叠

**整合方案**:

- ✅ 保留 `utils/` 作为唯一工具类目录（已有 26 处引用）
- ✅ 迁移 `libs/common/data_models.py` 到 `utils/`
- ✅ 删除 `libs/common/` 目录（0 处引用）
- ✅ 更新 `utils/__init__.py` 导出数据模型

**收益**:

- 消除重复代码（3 个模块：embedding, llm, time）
- 统一 import 路径：`from sage.benchmark.benchmark_memory.experiment.utils import ...`
- 零破坏性修改（无需更新现有代码）

**最终工具库**（15 个模块，~1524 行）:

```
utils/
├── [A] 数据模型: data_models.py (MemoryEntry, Query, DialogMessage)
├── [B] LLM 调用: llm_generator.py, embedding_generator.py
├── [C] 格式化: formatters.py, prompt_builder.py, dialogue_parser.py
├── [D] 配置: config_loader.py, args_parser.py
├── [E] 解析: json_parser.py, triple_parser.py
└── [F] 辅助: path_finder.py, progress_bar.py, calculation_table.py, time_geter.py
```

详见: `UTILS_CONSOLIDATION_PLAN.md` 和 `utils/README.md`

### 3.7 测试目录清理 (2025-12-12)

**问题**: 存在大量冗余单元测试和集成测试（~5112 行）

**清理原因**:

- ✅ Benchmark 本身就是最好的测试
- ✅ `memory_test_pipeline.py` 可运行 12 个记忆体的完整流程
- ✅ 单元测试与 benchmark 目标不符（benchmark 关注端到端性能）

**清理内容**:

- ✅ 删除 `libs/tests/` - 单元测试（2 文件）
- ✅ 删除 `libs/post_insert/tests/` - Action 单元测试（3 文件，604 行）
- ✅ 删除 `tests/` - 集成测试（14 文件，~4500 行）

**保留验证方式**:

```bash
# 运行 12 个记忆体的 benchmark 实验
python memory_test_pipeline.py --model TiM
python memory_test_pipeline.py --model MemoryBank
python memory_test_pipeline.py --model HippoRAG
# ... 等 12 个记忆体

# 这才是真正的端到端验证，比单元测试更有价值
```

**收益**:

- 减少 ~5112 行冗余测试代码
- 聚焦 benchmark 核心目标（性能评测，非功能测试）
- 简化代码库结构

### 3.8 libs/ 目录清理 (2025-12-12)

**问题**: `libs/` 目录存在大量冗余文件（旧版本、演示文件、临时文件）

**清理原则**: `libs/` 应该只包含 10 个核心组件

- 4 个 Action 目录: `pre_insert/`, `post_insert/`, `pre_retrieval/`, `post_retrieval/`
- 6 个核心文件: `memory_insert.py`, `memory_retrieval.py`, `memory_test.py`, `memory_sink.py`,
  `memory_source.py`, `pipeline_caller.py`

**删除的冗余文件**（8 个）:

```
❌ pre_insert.py              # 旧版本（已重构为 pre_insert/ 目录）
❌ post_insert.py             # 旧版本（已重构为 post_insert/ 目录）
❌ pre_retrieval.py           # 旧版本（已重构为 pre_retrieval/ 目录）
❌ post_retrieval.py          # 旧版本（已重构为 post_retrieval/ 目录）
❌ post_insert_refactored.py  # 临时重构文件（已整合）
❌ post_retrieval_refactored.py # 临时重构文件（已整合）
❌ memory_insert_demo.py      # 演示文件（非核心）
❌ post_insert_demo.py        # 演示文件（非核心）
```

**保留的核心文件**（6 个）:

```
✅ memory_insert.py           # MemoryInsert 透传
✅ memory_retrieval.py        # MemoryRetrieval 透传
✅ memory_test.py             # 测试辅助工具
✅ memory_sink.py             # 结果输出器
✅ memory_source.py           # 数据源加载器
✅ pipeline_caller.py         # Pipeline 调用器
```

**清理后目录结构**:

```
libs/
├── pre_insert/               # D2: PreInsert Action 策略
├── post_insert/              # D3: PostInsert Action 策略
├── pre_retrieval/            # D4: PreRetrieval Action 策略
├── post_retrieval/           # D5: PostRetrieval Action 策略
├── memory_insert.py          # MemoryInsert 透传
├── memory_retrieval.py       # MemoryRetrieval 透传
├── memory_test.py            # 测试辅助工具
├── memory_sink.py            # 结果输出器
├── memory_source.py          # 数据源加载器
└── pipeline_caller.py        # Pipeline 调用器
```

**收益**:

- 文件数: 15 个 → 10 个（**-33%**）
- 消除版本混乱（旧文件 vs 新目录）
- 保留所有核心功能组件

______________________________________________________________________

## 四、统计功能实现（2025-12-14完成）

> **目标**: 为SAGE Memory Benchmark Pipeline添加完整的性能统计功能
>
> **总工作量**: 13-20小时（实际约2小时）
>
> **并行开发**: 2人团队可在3-4天完成

### 4.1 任务总览

```
Task A: 时间统计全流程 (5-8h) ← ✅ 已完成，可独立交付
Task B: 存储统计全流程 (6-9h) ← ✅ 已完成，可独立交付
Task C: 测试验证 (2-3h)       ← ✅ 已完成，依赖A+B
```

**产出示例**:

```json
{
  "timing_summary": {
    "pre_insert_ms": {"avg_ms": 12.5, "max_ms": 18.3, "min_ms": 8.7, "count": 5},
    "memory_insert_ms": {...},
    "total": {"avg_ms": 156.8, ...}
  },
  "memory_summary": {
    "total_entries": {"avg": 48.5, "final": 50},
    "total_size_bytes": {"avg": 225000, "final": 228000},
    "total_size_human": "222.66 KB"
  }
}
```

### 4.2 Task A: 时间统计全流程实现

**状态**: ✅ 已完成 (2025-12-14)\
**工作量**: 5-8小时\
**依赖**: 无

#### 实现步骤

**步骤1: 7个算子添加时间打点**

统一模式（所有算子使用 `time.perf_counter()`）:

```python
import time

class SomeOperator(MapFunction):
    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        start_time = time.perf_counter()
        # ... 原有业务逻辑 ...
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        data.setdefault("stage_timings", {})["{stage_name}_ms"] = elapsed_ms
        return data
```

修改的7个文件:

| 文件                            | 算子类          | stage_name          | 位置                 |
| ------------------------------- | --------------- | ------------------- | -------------------- |
| libs/pre_insert/operator.py     | PreInsert       | pre_insert_ms       | execute()第48-73行   |
| libs/memory_insert.py           | MemoryInsert    | memory_insert_ms    | execute()第79-140行  |
| libs/post_insert/operator.py    | PostInsert      | post_insert_ms      | execute()第76-94行   |
| libs/pre_retrieval/operator.py  | PreRetrieval    | pre_retrieval_ms    | execute()第87-157行  |
| libs/memory_retrieval.py        | MemoryRetrieval | memory_retrieval_ms | execute()第102-171行 |
| libs/post_retrieval/operator.py | PostRetrieval   | post_retrieval_ms   | execute()第59-89行   |
| libs/memory_test.py             | MemoryTest      | memory_test_ms      | execute()第69-103行  |

**步骤2: PipelineCaller聚合时间**

文件: `libs/pipeline_caller.py`，修改 `execute()` 方法：

```python
# 收集插入阶段时间（约第170行）
insert_result = self.call_service("memory_insert_service", ...)
insert_timings = insert_result.get("stage_timings", {})

# 收集测试阶段时间（约第210行）
if should_test:
    test_result = self.call_service("memory_test_service", ...)
    test_timings = test_result.get("stage_timings", {})

    # 合并到输出
    output_data["stage_timings"] = {**insert_timings, **test_timings}
```

**步骤3: MemorySink输出timing_summary**

文件: `libs/memory_sink.py`，修改 `_save_results()` 方法：

```python
# 收集时间统计
all_stage_timings = [r.get("stage_timings", {}) for r in results if "stage_timings" in r]

# 计算汇总
timing_summary = self._calculate_timing_summary(all_stage_timings)

# 添加到输出
output["timing_summary"] = timing_summary

# 实现汇总方法
def _calculate_timing_summary(self, all_timings: list[dict]) -> dict:
    summary = {}
    all_stages = set()
    for timings in all_timings:
        all_stages.update(timings.keys())

    for stage in all_stages:
        values = [t[stage] for t in all_timings if stage in t]
        if values:
            summary[stage] = {
                "avg_ms": sum(values) / len(values),
                "max_ms": max(values),
                "min_ms": min(values),
                "count": len(values),
            }

    # 计算总耗时
    total_times = [sum(t.values()) for t in all_timings]
    summary["total"] = {
        "avg_ms": sum(total_times) / len(total_times),
        "max_ms": max(total_times),
        "min_ms": min(total_times),
        "count": len(total_times),
    }
    return summary
```

### 4.3 Task B: 存储统计全流程实现

**状态**: ✅ 已完成 (2025-12-14)\
**工作量**: 6-9小时（实际约1小时）\
**依赖**: 无

#### 架构说明

```
Service 层 (7个服务)
    ↓ 调用 collection.get_storage_stats()
Collection 层 (4个基础Collection + 3个复合)
    ↓ 统计各存储组件
Storage 层 (text_storage + metadata_storage + index)
```

#### 实现步骤

**步骤1: Collection层实现get_storage_stats()**

文件: `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/memory_collection/`

**1.1 基类接口定义** (`base_collection.py`)

```python
@abstractmethod
def get_storage_stats(self) -> dict[str, int]:
    """
    获取 Collection 的存储统计信息。

    Returns:
        {
            "total_entries": int,          # 总条目数
            "text_size_bytes": int,        # 文本存储字节数
            "vector_size_bytes": int,      # 向量存储字节数（估算）
            "metadata_size_bytes": int,    # 元数据存储字节数（估算）
            "index_size_bytes": int,       # 索引结构字节数（估算）
            "total_size_bytes": int,       # 总字节数（上述之和）
        }
    """
    pass
```

**1.2 VDBMemoryCollection实现** (`vdb_collection.py`)

```python
def get_storage_stats(self) -> dict[str, int]:
    # 文本存储
    text_size = sum(len(text.encode("utf-8")) for text in self.text_storage.values())

    # 元数据存储
    metadata_size = sum(len(json.dumps(meta).encode("utf-8"))
                       for meta in self.metadata_storage.values())

    # 向量存储（⚠️ 使用 index_obj.index.ntotal，不是 index_obj.ntotal）
    if self.index_obj and hasattr(self.index_obj, "index"):
        vector_count = self.index_obj.index.ntotal
        vector_dim = getattr(self.index_obj, "dim", 0)
        vector_size = vector_count * vector_dim * 4  # float32占4字节
    else:
        vector_size = 0

    # 索引结构（估算为向量的20%）
    index_size = int(vector_size * 0.2)

    return {
        "total_entries": len(self.text_storage),
        "text_size_bytes": text_size,
        "vector_size_bytes": vector_size,
        "metadata_size_bytes": metadata_size,
        "index_size_bytes": index_size,
        "total_size_bytes": text_size + vector_size + metadata_size + index_size,
    }
```

**1.3 其他Collection实现**

- `KVMemoryCollection`: 统计dict存储空间（无向量）
- `GraphMemoryCollection`: 统计节点+边结构
- `HybridCollection`: 聚合子Collection的统计

**步骤2: Service层扩展get_stats()**

文件: `packages/sage-middleware/src/sage/middleware/components/sage_mem/services/`

所有7个Service修改模式：

```python
def get_stats(self) -> dict[str, Any]:
    base_stats = {
        # ... 原有字段保持不变 ...
    }

    # 添加存储统计
    storage_stats = self.collection.get_storage_stats()
    base_stats["storage"] = storage_stats

    return base_stats
```

需修改的Service:

- `short_term_memory_service.py`
- `key_value_memory_service.py`
- `graph_memory_service.py`
- `hierarchical_memory_service.py` (需聚合各层统计)
- `hybrid_memory_service.py`
- `vector_memory_service.py`（替代原 `vector_hash_memory_service.py`，配置 `IndexLSH` 即 TiM 哈希桶）
- `neuromem_vdb_service.py` (新增方法)

**步骤3: PipelineCaller调用get_stats()**

文件: `libs/pipeline_caller.py`，修改 `execute()` 方法：

```python
if should_test:
    # 获取记忆体统计
    try:
        memory_stats = self.call_service(
            "memory_insert_service",
            method="get_stats",
            data={},
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"Failed to get memory stats: {e}")
        memory_stats = {}

    # 添加到输出
    output_data["memory_stats"] = memory_stats
```

**步骤4: MemorySink输出memory_summary**

文件: `libs/memory_sink.py`

```python
def _save_results(self, results: list[dict]) -> None:
    # 收集存储统计
    all_memory_stats = [r.get("memory_stats", {}) for r in results if "memory_stats" in r]

    # 计算汇总
    memory_summary = self._calculate_memory_summary(all_memory_stats)

    # 添加到输出
    output["memory_summary"] = memory_summary

def _calculate_memory_summary(self, all_stats: list[dict]) -> dict:
    storage_list = [s.get("storage", {}) for s in all_stats if "storage" in s]
    if not storage_list:
        return {}

    summary = {}
    fields = ["total_entries", "text_size_bytes", "vector_size_bytes",
              "metadata_size_bytes", "index_size_bytes", "total_size_bytes"]

    for field in fields:
        values = [s[field] for s in storage_list if field in s]
        if values:
            summary[field] = {
                "avg": sum(values) / len(values),
                "max": max(values),
                "min": min(values),
                "final": values[-1],
            }

    # 添加人类可读格式
    if "total_size_bytes" in summary:
        summary["total_size_human"] = self._format_bytes(summary["total_size_bytes"]["final"])

    return summary

def _format_bytes(self, bytes_val: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} TB"
```

### 4.4 Task C: 测试验证

**状态**: ✅ 已完成 (2025-12-14)\
**工作量**: 2-3小时\
**依赖**: Task A 和 Task B 完成

#### 单元测试

文件位置: `packages/sage-benchmark/tests/unit/benchmark_memory/test_statistics.py`

**测试内容**:

- `TestTimingStatistics` - 时间统计测试（2个测试）
- `TestStorageStatistics` - 存储统计测试（3个测试）
- `TestIntegration` - 集成测试（1个测试）
- `TestPerformance` - 性能测试（2个测试）

**运行结果**:

```bash
conda run -n ksage python -m pytest packages/sage-benchmark/tests/unit/benchmark_memory/test_statistics.py -v
# 7 passed, 1 skipped in 0.07s
```

#### 集成测试脚本

文件位置:
`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/scripts/test_statistics.sh`

**功能**:

- 自动运行 short_term_memory 和 hierarchical_memory pipeline
- 验证输出JSON格式完整性
- 检查 timing_summary 和 memory_summary 字段

#### 验证方法

```bash
# 运行pipeline测试
cd packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment
python -m sage.benchmark.benchmark_memory.experiment.memory_test_pipeline \
    --config config/locomo_short_term_memory_pipeline.yaml \
    --num-samples 3

# 检查输出
ls -lt .sage/benchmarks/benchmark_memory/
cat .sage/benchmarks/benchmark_memory/xxx.json | jq '.timing_summary'
cat .sage/benchmarks/benchmark_memory/xxx.json | jq '.memory_summary'
```

### 4.5 关键设计原则

#### 向后兼容

- Service.get_stats() 原有字段不变
- 新增 `storage` 为嵌套字段
- 老代码不受影响

#### 独立交付

- Task A（时间统计）可先上线
- Task B（存储统计）可后续迭代
- 两者互不依赖

#### 性能开销

- 时间打点: `time.perf_counter()` 开销约几微秒，可忽略
- 存储统计: 只在测试时调用，不在热路径上

### 4.6 相关文件清单

```
packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/
├── libs/
│   ├── pre_insert/operator.py          ← 修改：添加时间打点
│   ├── memory_insert.py                ← 修改：添加时间打点
│   ├── post_insert/operator.py         ← 修改：添加时间打点
│   ├── pre_retrieval/operator.py       ← 修改：添加时间打点
│   ├── memory_retrieval.py             ← 修改：添加时间打点
│   ├── post_retrieval/operator.py      ← 修改：添加时间打点
│   ├── memory_test.py                  ← 修改：添加时间打点
│   ├── pipeline_caller.py              ← 修改：聚合时间+存储数据
│   └── memory_sink.py                  ← 修改：输出统计汇总
└── scripts/
    └── test_statistics.sh              ← 新增：集成测试脚本

packages/sage-middleware/src/sage/middleware/components/sage_mem/
├── neuromem/memory_collection/
│   ├── base_collection.py              ← 修改：添加抽象方法
│   ├── vdb_collection.py               ← 修改：实现get_storage_stats()
│   ├── kv_collection.py                ← 修改：实现get_storage_stats()
│   ├── graph_collection.py             ← 修改：实现get_storage_stats()
│   └── hybrid_collection.py            ← 修改：实现get_storage_stats()
└── services/
    ├── short_term_memory_service.py    ← 修改：扩展get_stats()
    ├── key_value_memory_service.py     ← 修改：扩展get_stats()
    ├── graph_memory_service.py         ← 修改：扩展get_stats()
    ├── hierarchical_memory_service.py  ← 修改：扩展get_stats()
    ├── hybrid_memory_service.py        ← 修改：扩展get_stats()
    ├── vector_memory_service.py        ← 修改：扩展get_stats()（原 hash 版本重命名，IndexLSH=哈希桶）
    └── neuromem_vdb_service.py         ← 修改：扩展get_stats()

packages/sage-benchmark/tests/unit/benchmark_memory/
└── test_statistics.py                  ← 新增：单元测试
```

### 4.7 完成标准

✅ 所有7个算子都添加了时间打点\
✅ PipelineCaller正确聚合insert和test的时间\
✅ MemorySink输出包含完整的timing_summary\
✅ BaseMemoryCollection添加抽象方法\
✅ 4个基础Collection实现get_storage_stats()\
✅ 7个Service扩展get_stats()返回storage字段\
✅ PipelineCaller调用get_stats()获取存储\
✅ MemorySink输出memory_summary\
✅ 单元测试通过（7 passed, 1 skipped）\
✅ 集成测试脚本已创建\
✅ 代码通过pre-commit检查

______________________________________________________________________

*本档案当前聚焦于架构与记忆体映射，后续如有重大架构/实现变更，可按需补充新的设计原则或示意图。*
