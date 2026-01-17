# 数据集说明（Dataset Overview）

本文档对 NeuroMem Benchmarks 所使用的核心数据集进行总结，重点介绍 LoCoMo 长轮对话数据集，并说明我们在实验平台中对其测试逻辑所做的改造。

---

## 1. 支持的数据集概览

当前实验平台主要支持以下三类数据集（与 `benchmarks/ARCHITECTURE.md` 保持一致）：

| 数据集 | 类型 | 规模 | 主要用途 |
|--------|------|------|----------|
| **LoCoMo** | 长轮对话 | 50+ 任务，每个 300–2000 轮 | 长期对话记忆评估（主数据集） |
| **Conflict Resolution** | 事实冲突 | 5530 个事实 | 事实冲突检测与消解 |
| **LongMemEval** | 长期记忆评估 | 多任务 | 综合性长记忆能力评估 |

在这三者中，LoCoMo 被用作 **主基准数据集**，承载了大部分记忆系统的对比实验。

---

## 2. 选择 LoCoMo 作为主基准的原因

### 2.1 长轮多会话对话场景

LoCoMo（Long-form Conversation Memory）专门用于测试 **长程对话记忆能力**，具有以下特征：

- **长对话长度**：单个任务（如 `conv-26`）通常包含数百到上千条消息（300–2000 轮），远长于一般对话数据集；
- **多会话结构**：每个任务内部包含多个 session（例如 2–3 个），可以覆盖跨会话记忆与上下文切换场景；
- **高密度监督信号**：每个任务配有约 150–200 个问题，覆盖用户画像、事实记忆、事件细节等不同类型。

这些特性使 LoCoMo 更接近 **真实应用中的多轮对话 Agent** 场景：记忆容量持续增长、对话跨 session 进行、问题混合考察多种能力（事实回忆、信息整合、遗漏检测等）。

### 2.2 Category 细粒度问题设计

LoCoMo 将问题划分为 5 类 Category（在 `benchmarks/evaluation/analysis/config/locomo.yaml` 和 `LoCoMoEvaluator` 中有专门处理）：

| Category | 问题类型 | 评估重点 |
|----------|---------|----------|
| **1** | 多答案问题 | 信息聚合与覆盖率 |
| **2** | 单答案事实 | 精确检索能力 |
| **3** | 含注释/噪声 | 文本清理与鲁棒性 |
| **4** | 标准单答案 | 基础检索性能 |
| **5** | 信息未提及 | 正负样本区分与“未提及”识别 |

评估模块中提供了专门的 `LoCoMoEvaluator`，在计算 Token-based F1 时对不同 Category 进行定制化处理（如多答案拆分、注释截断等），从而在 **一个统一的数据集上同时考察多种记忆维度**。

### 2.3 与其他数据集的互补关系

- 相比 **Conflict Resolution**：LoCoMo 侧重对话和时序上下文，而非孤立事实冲突；
- 相比 **LongMemEval**：LoCoMo 提供了更明确的多轮对话结构和丰富的 QA 标注，便于对记忆系统做精细对比；
- 在本文实验中，LoCoMo 被用作 **记忆结构/策略的主对比基准**，其他数据集更多用于专项评估和补充分析。

---

## 3. LoCoMo 在实验平台中的加载方式

### 3.1 统一数据加载接口

在实验 Pipeline 中，所有数据集都通过统一的 `DataLoaderFactory` 创建加载器：

```python
from benchmarks.experiment.utils.dataloader import DataLoaderFactory

loader = DataLoaderFactory.create("locomo")
```

对于 LoCoMo，对应适配器为 `LocomoAdapter`：

```python
# benchmarks/experiment/utils/dataloader/adapters/locomo_adapter.py
class LocomoAdapter(BaseDataLoader):
    """Locomo 数据集适配器

    Locomo 是长轮对话记忆数据集。
    """

    def sessions(self, task_id: str) -> list[tuple[int, int]]: ...
    def get_dialog(self, task_id: str, session_x: int, dialog_y: int) -> list[dict]: ...
    def get_evaluation(self, task_id: str, session_x: int, dialog_y: int) -> list[dict]: ...
    def dialog_count(self, task_id: str) -> int: ...
    def message_count(self, task_id: str) -> int: ...
```

### 3.2 MemorySource：按对话轮次流式输出

主 Pipeline 的数据源 `MemorySource`（`benchmarks/experiment/libs/memory_source.py`）基于上述 Adapter，将 LoCoMo 样本拆分为细粒度的“对话包”：

```python
# 初始化：打印任务统计信息
self.turns = self.loader.sessions(self.task_id)
self.total_messages = self.loader.message_count(self.task_id)
self.total_dialogs = self.loader.dialog_count(self.task_id)

# execute() 每次返回一个数据包
result = {
    "task_id": self.task_id,
    "session_id": session_id,
    "dialog_id": self.dialog_ptr,
    "dialogs": dialogs,           # 当前插入的 1~N 条消息
    "dialog_len": len(dialogs),
    "packet_idx": self.packet_idx,
    "total_packets": self.total_dialogs,
    "is_session_end": is_session_end,
}
```

这样，原本一次性加载的长对话被拆分为按轮次递增的流式数据，使得后续记忆插入/测试可以在时间维度上精细控制。

---

## 4. 对原有 LoCoMo 测试逻辑的改造

原始 LoCoMo 更偏向于 **离线一次性评估**：加载完整对话历史后，对所有问题统一进行测试。这种方式难以回答以下问题：

- 记忆体在“记忆逐步累积”的过程中性能如何变化？
- 不同记忆策略（如遗忘曲线、合并策略）对 **性能演化曲线** 有何影响？

为此，NeuroMem Benchmarks 在 `memory_test_pipeline.py` 与 `PipelineCaller` 中对测试逻辑进行了系统改造。

### 4.1 增量式（Incremental）测试机制

核心思想：

> **不是在对话结束后一次性评估，而是在对话进行过程中，定期对“当前已可见的问题集合”进行测试。**

具体做法：

1. 预先根据问题总数和 `test_segments` 参数，计算一组测试阈值：

   ```python
   # 例如 total_questions = 199, test_segments = 5
   test_thresholds = calculate_test_thresholds(
       total_questions=199,
       test_segments=5,
   )
   # → [40, 80, 120, 160, 199]
   ```

2. 在 `PipelineCaller` 中，随着对话轮次推进，持续检查“当前可见的问题数”是否达到下一个阈值：

   ```python
   current_questions = loader.get_evaluation(
       task_id,
       session_x=session_id,
       dialog_y=dialog_id + dialog_len - 1,
   )

   current_count = len(current_questions)

   if current_count >= next_threshold:
       # 触发一次阶段性测试：
       # 测试所有当前可见的问题（如前 40/80/... 个）
       run_memory_test_for_visible_questions()
   ```

3. 每次触发测试时，**仅允许访问当前对话位置之前的对话与记忆**，从而严格避免“未来信息泄露”。

### 4.2 测试过程中的可见性控制

对于给定任务 `conv-26`：

- 当对话推进到早期轮次时，可能只有前 40 个问题可见；
- 随着更多对话被插入，评估函数 `get_evaluation(...)` 会返回更长的问题前缀（80、120、160...）；
- 每次阶段性测试仅在这一前缀上计算 F1/EM 等指标，并单独记录。

结果上，我们为每个记忆系统获得了一条关于 **问题数量 → 性能** 的演化曲线，而非一组单点指标。

### 4.3 与记忆五维框架的结合

增量式 LoCoMo 测试逻辑与五维实验框架（D1–D5）深度结合：

- **D1 Memory Service**：不同记忆体结构（如 FIFO、LSH、Knowledge Graph）在对话推进过程中的表现差异；
- **D2 PreInsert / D3 PostInsert**：不同归一化策略、合并/遗忘策略对长期性能演化的影响；
- **D4 PreRetrieval / D5 PostRetrieval**：不同 Query Formulation 与 Context Integration 策略在 LoCoMo 上的对比实验（对应多个 `*_locomo_*.yaml` 配置与 `run_*locomo*.sh` 脚本）。

这种设计使 LoCoMo 不仅是一个“打分数据集”，而是一个 **驱动记忆系统全链路对比与消融实验的主干数据集**。

---

## 5. 小结

- LoCoMo 因其 **长对话、多会话结构、细粒度问题标注**，被选为 NeuroMem Benchmarks 的主基准数据集；
- 通过 `LocomoAdapter + MemorySource`，原始 LoCoMo 被重构为适合 Pipeline 流式处理的数据源；
- 通过增量式测试逻辑，我们可以在 LoCoMo 上观察各类记忆系统在“记忆不断累积”过程中的性能变化，而不仅仅是终局表现；
- 该设计与五维实验框架（D1–D5）紧密结合，为论文中的 **Dataset Selection** 和 **Evaluation Protocol** 提供了统一的技术基础。
