# NeuroMem Benchmarks - 架构分析文档

> **文档版本**: v1.0  
> **最后更新**: 2026-01-09  
> **适用范围**: NeuroMem v0.2.1+

---

## 📋 目录

- [1. 总体架构](#1-总体架构)
- [2. experiment 模块](#2-experiment-模块)
  - [2.1 核心 Pipeline 架构](#21-核心-pipeline-架构)
  - [2.2 libs 组件库](#22-libs-组件库)
  - [2.3 配置系统](#23-配置系统)
  - [2.4 实验脚本](#24-实验脚本)
  - [2.5 工具集](#25-工具集)
- [3. evaluation 模块](#3-evaluation-模块)
- [4. 数据流与执行流程](#4-数据流与执行流程)
- [5. 扩展开发指南](#5-扩展开发指南)
- [6. 最佳实践](#6-最佳实践)

---

## 1. 总体架构

NeuroMem Benchmarks 是一个基于 **Pipeline 架构**的记忆系统评测框架，用于测试和对比各种长程对话记忆算法在标准数据集上的表现。

### 1.1 模块划分

```
benchmarks/
├── experiment/          # 实验执行模块（核心）
│   ├── memory_test_pipeline.py    # 主入口
│   ├── libs/                      # Pipeline 组件库
│   ├── config/                    # 配置文件
│   ├── script/                    # 批量执行脚本
│   ├── utils/                     # 工具集
│   ├── tools/                     # 辅助工具
│   └── docs/                      # 实验文档
│
└── evaluation/         # 结果评估模块
    ├── specialized_analysis/      # 专项分析脚本
    └── README.md                  # 评估说明
```

### 1.2 设计理念

1. **Pipeline 驱动**: 采用 SAGE Kernel 的 Pipeline 框架，实现流式数据处理
2. **可配置性**: 所有算法参数、Prompt、数据集通过 YAML 配置
3. **策略模式**: Pre/Post Operator 采用策略模式，支持灵活组合
4. **标准化输出**: 统一的数据结构和评估指标，便于跨算法对比
5. **模块化设计**: 各组件职责单一，易于扩展和维护

### 1.3 支持的数据集

| 数据集 | 类型 | 规模 | 特点 |
|--------|------|------|------|
| **LoCoMo** | 长轮对话 | 50+ 任务，每个 300-2000 轮 | 包含 5 类问题，测试多种能力 |
| **Conflict Resolution** | 事实冲突 | 5530 个事实 | 测试冲突解决能力 |
| **LongMemEval** | 长记忆评估 | 多任务 | 综合性评估 |

---

## 2. experiment 模块

实验执行模块是 Benchmarks 的核心，负责加载数据、运行算法、收集结果。

### 2.1 核心 Pipeline 架构

#### 2.1.1 三层 Pipeline 设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                        主 Pipeline                                  │
│  MemorySource → PipelineCaller → MemorySink                        │
└─────────────────────────────────────────────────────────────────────┘
                        ↓ (调用子 Pipeline)
        ┌───────────────────────────────────────────────────┐
        │  插入 Pipeline (memory_insert_service)            │
        │  PreInsert → MemoryInsert → PostInsert            │
        └───────────────────────────────────────────────────┘
                        ↓ (调用子 Pipeline)
        ┌───────────────────────────────────────────────────┐
        │  测试 Pipeline (memory_test_service)              │
        │  PreRetrieval → MemoryRetrieval → PostRetrieval   │
        │  → MemoryEvaluation                               │
        └───────────────────────────────────────────────────┘
```

**设计要点**:
- **主 Pipeline**: 控制整体流程，逐个处理数据包
- **插入 Pipeline**: 负责记忆的预处理、存储、后处理
- **测试 Pipeline**: 负责查询处理、检索、结果生成、评估
- **背压机制**: 主 Pipeline 通过服务调用实现 one-by-one 处理

#### 2.1.2 Pipeline 入口

文件: [`memory_test_pipeline.py`](./experiment/memory_test_pipeline.py)

```python
def main():
    # 1. 解析配置
    args = parse_args()
    config = RuntimeConfig.load(args.config, args.task_id)

    # 2. 创建环境
    env = LocalEnvironment("memory_test_experiment")

    # 3. 注册记忆服务（通过工厂模式）
    services_type = config.get("services.services_type")
    factory = NeuromemServiceFactory.create(services_type, config)
    env.register_service_factory(registered_name, factory)

    # 4. 注册 Pipeline 服务
    env.register_service("memory_insert_service", PipelineService, ...)
    env.register_service("memory_test_service", PipelineService, ...)

    # 5. 构建三层 Pipeline
    # 插入 Pipeline
    env.from_source(...).map(PreInsert).map(MemoryInsert).map(PostInsert).sink(...)
    # 测试 Pipeline
    env.from_source(...).map(PreRetrieval).map(MemoryRetrieval).map(PostRetrieval).map(MemoryEvaluation).sink(...)
    # 主 Pipeline
    env.from_batch(MemorySource).map(PipelineCaller).sink(MemorySink)

    # 6. 启动执行
    env.submit(autostop=True)
```

---

### 2.2 libs 组件库

组件库包含 Pipeline 的所有算子实现，按职责分为 **Source/Sink**、**核心算子**、**策略算子**。

#### 2.2.1 Source/Sink 组件

| 组件 | 类型 | 职责 |
|------|------|------|
| **MemorySource** | Source | 从数据集逐个加载对话轮次，输出数据包 |
| **MemorySink** | Sink | 收集测试结果，生成 JSON 报告 |

**MemorySource 输出格式**:
```python
{
    "packet_idx": 0,                    # 数据包序号
    "session_id": "session_1",          # 会话 ID
    "dialogs": [                        # 对话列表（1 条或 2 条）
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "total_packets": 500,               # 总数据包数
    "current_question_count": 10,       # 当前累计问题数
    "visible_questions": [...]          # 当前可见的所有问题
}
```

**MemorySink 输出文件**:
```
.sage/output/benchmarks/benchmark_memory/{dataset}/{date}/{memory_name}/{task_id}_{timestamp}.json
```

#### 2.2.2 核心算子

| 算子 | Pipeline | 职责 | 输入 | 输出 |
|------|----------|------|------|------|
| **PipelineCaller** | 主 | 协调插入/测试，决定何时触发测试 | 数据包 | 测试结果 |
| **MemoryInsert** | 插入 | 调用记忆服务的 `insert()` 方法 | memory_entries | insert_stats |
| **MemoryRetrieval** | 测试 | 调用记忆服务的 `retrieve()` 方法 | question + query_embedding | memory_data |
| **MemoryEvaluation** | 测试 | 使用 LLM 生成答案并评估 | question + history_text | answer |

**设计原则**:
- **纯透传**: 核心算子只负责调用，不做数据转换
- **性能监控**: 记录每步耗时，便于性能分析
- **错误容忍**: 单条失败不影响整体流程

#### 2.2.3 策略算子（Pre/Post Operators）

采用 **策略模式 + 注册表** 设计，支持灵活组合不同的预处理/后处理策略。

##### PreInsert 策略（记忆插入前预处理）

目录: `libs/pre_insert/`

```
pre_insert/
├── operator.py         # PreInsert 主算子
├── registry.py         # Action 注册表
├── base.py             # 基类和数据模型
├── none_action.py      # 透传策略
├── transform/          # 文本转换策略
├── extract/            # 知识提取策略
└── score/              # 重要性评分策略
```

**支持的 Actions**:

| Action | 说明 | 条目数 | 应用场景 |
|--------|------|--------|----------|
| `none` | 透传原始对话 | 1 条 | STM, 基础测试 |
| `transform` | 文本格式转换 | 1 条 | 格式标准化 |
| `extract` | 提取事实/实体 | N 条 | 知识抽取 |
| `score` | 重要性评分 | 1 条 | 选择性遗忘 |
| `multi_embed` | 多向量生成 | 1 条 | ReMI 算法 |
| `tri_embed` | 三元组提取 | N 条 | 知识图谱 |

**配置示例**:
```yaml
operators:
  pre_insert:
    action: "extract"
    extract_prompt: |
      Extract all facts from the conversation.
      Output JSON array: [{"fact": "..."}, ...]
```

##### PostInsert 策略（记忆插入后处理）

目录: `libs/post_insert/`

```
post_insert/
├── operator.py         # PostInsert 主算子
├── registry.py         # Action 注册表
├── none_action.py      # 透传策略
├── distillation/       # 摘要压缩策略
├── forgetting/         # 遗忘机制策略
├── link_evolution/     # 链接演化策略（A-Mem）
├── crud/               # 增删改查策略
├── enhance/            # 记忆增强策略
└── migrate/            # 记忆迁移策略
```

**支持的 Actions**:

| Action | 说明 | 应用场景 |
|--------|------|----------|
| `none` | 无后处理 | 大多数算法 |
| `summarize` | 生成摘要 | MemoryBank, LD-Agent |
| `time_decay` | 时间衰减 | 遗忘机制 |
| `link_evolution` | 链接演化 | A-Mem 算法 |
| `deduplication` | 去重 | 数据清洗 |

##### PreRetrieval 策略（记忆检索前预处理）

目录: `libs/pre_retrieval/`

```
pre_retrieval/
├── operator.py         # PreRetrieval 主算子
├── registry.py         # Action 注册表
├── none_action.py      # 透传策略
├── embedding/          # 查询向量化策略
├── optimize/           # 查询优化策略
└── validate/           # 查询验证策略
```

**支持的 Actions**:

| Action | 说明 | 应用场景 |
|--------|------|----------|
| `none` | 透传查询 | 基础检索 |
| `query_expansion` | 查询扩展 | 提高召回率 |
| `query_rewrite` | 查询改写 | 语义优化 |

##### PostRetrieval 策略（记忆检索后处理）

目录: `libs/post_retrieval/`

```
post_retrieval/
├── operator.py         # PostRetrieval 主算子
├── registry.py         # Action 注册表
├── none_action.py      # 透传策略（默认格式化对话历史）
├── rerank/             # 重排序策略
├── filter/             # 过滤策略
├── augment/            # 增强策略
└── merge/              # 合并策略
```

**支持的 Actions**:

| Action | 说明 | 应用场景 |
|--------|------|----------|
| `none` | 格式化对话历史 | 所有算法（默认） |
| `rerank_relevance` | 相关性重排 | 提高精度 |
| `filter_threshold` | 阈值过滤 | 去除噪声 |
| `context_compression` | 上下文压缩 | 减少 token 消耗 |

---

### 2.3 配置系统

#### 2.3.1 配置文件结构

```
config/
├── template_full.yaml                  # 完整配置模板（1099 行）
├── primitive_memory_model/             # 原始记忆模型配置
│   ├── locomo_short_term_memory_pipeline.yaml  (STM)
│   ├── locomo_scm_pipeline.yaml        (SCM)
│   ├── locomo_tim_pipeline.yaml        (TiM)
│   ├── locomo_secom_pipeline.yaml      (SECOM)
│   └── ...其他 10+ 算法
├── consolidation_policy/               # 巩固策略配置
├── context_integration_mechanism/      # 上下文整合配置
├── memory_data_structure/              # 数据结构配置
├── normalization_strategy/             # 归一化策略配置
├── query_formulation_strategy/         # 查询策略配置
└── result_optimization_strategy/       # 结果优化配置
```

#### 2.3.2 配置文件格式

配置分为 4 个主要部分：

```yaml
# ============================================================
# 1. 运行时配置
# ============================================================
runtime:
  dataset: "locomo"                 # 数据集名称
  memory_insert_verbose: false      # 是否打印插入详情
  memory_test_verbose: true         # 是否打印测试详情
  test_segments: 10                 # 测试分段数

  # LLM 配置
  api_key: "..."
  base_url: "http://..."
  model_name: "..."
  max_tokens: 256
  temperature: 0
  seed: 42

  # Embedding 配置
  embedding_base_url: "http://..."
  embedding_model: "..."

  # Prompt 模板
  prompt_template: |
    Based on the context, answer the question.
    Question: {question}
    Answer:

# ============================================================
# 2. 服务配置
# ============================================================
services:
  services_type: "partitional.fifo_queue"  # 服务类型
  fifo_queue:                               # 服务参数
    max_size: 5
    vector_dim: 1024
    retrieval_mode: "recent_first"
    retrieval_top_k: 10

# ============================================================
# 3. Operator 配置
# ============================================================
operators:
  pre_insert:
    action: "none"                  # Action 类型
    # action 特定参数

  post_insert:
    action: "none"

  pre_retrieval:
    action: "none"

  post_retrieval:
    action: "none"
    conversation_format_prompt: |
      The following is history information.

# ============================================================
# 4. 高级配置（可选）
# ============================================================
advanced:
  timeout_seconds: 300
  retry_count: 3
  log_level: "INFO"
```

#### 2.3.3 配置加载机制

文件: `utils/config/runtime_config.py`

```python
class RuntimeConfig:
    @staticmethod
    def load(config_path: str, task_id: str = None):
        """加载配置文件

        Args:
            config_path: YAML 文件路径
            task_id: 任务 ID（可覆盖配置文件中的值）

        Returns:
            RuntimeConfig 对象
        """

    def get(self, key: str, default=None):
        """获取配置值（支持点分隔路径）

        Examples:
            config.get("runtime.dataset")  # "locomo"
            config.get("services.fifo_queue.max_size")  # 5
        """
```

---

### 2.4 实验脚本

#### 2.4.1 脚本组织

```
script/
├── primitive_memory_model/
│   ├── run_locomo_stm.sh               # LoCoMo STM 批量测试
│   ├── run_locomo_tim.sh               # LoCoMo TiM 批量测试
│   └── ...
├── consolidation_policy/
├── context_integration_mechanism/
├── memory_data_structure/
├── normalization_strategy/
├── query_formulation_strategy/
├── result_optimization_strategy/
├── run_conflict_resolution_stm.sh      # Conflict Resolution 测试
└── run_longmemeval_stm.sh              # LongMemEval 测试
```

#### 2.4.2 脚本结构

以 [`run_locomo_stm.sh`](./experiment/script/primitive_memory_model/run_locomo_stm.sh) 为例：

```bash
#!/bin/bash
set -e

# 1. 路径配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../../config/primitive_memory_model/locomo_short_term_memory_pipeline.yaml"

# 2. 定义任务列表
TASK_IDS=(
  "conv-26"
  "conv-30"
  "conv-41"
  # ... 50+ 任务
)

# 3. 创建日志目录
DATASET="locomo"
DATE=$(date +%Y%m%d)
MEMORY_NAME="STM"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$DATE/$MEMORY_NAME"

# 4. 批量执行
for TASK_ID in "${TASK_IDS[@]}"; do
  TIMESTAMP=$(date +%H%M%S)
  LOG_FILE="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}.log"

  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" \
    python "$PYTHON_SCRIPT" \
    --config "$CONFIG_FILE" \
    --task_id "$TASK_ID" \
    2>&1 | tee "$LOG_FILE"
done
```

**使用方法**:
```bash
cd benchmarks/experiment
bash script/primitive_memory_model/run_locomo_stm.sh
```

---

### 2.5 工具集

#### 2.5.1 utils 工具模块

目录: `utils/`

```
utils/
├── config/                         # 配置管理
│   ├── runtime_config.py           # 配置加载器
│   └── parse_args.py               # 命令行参数解析
├── llm/                            # LLM 调用层
│   ├── llm_generator.py            # LLM 文本生成
│   └── embedding_generator.py      # Embedding 生成
├── helpers/                        # 辅助函数
│   ├── path_utils.py               # 路径工具
│   ├── time_utils.py               # 时间格式化
│   └── test_thresholds.py          # 测试阈值计算
└── ui/                             # UI 组件
    └── progress_bar.py             # 进度条
```

**关键工具类**:

1. **LLMGenerator** - LLM 调用封装
   ```python
   generator = LLMGenerator.from_config(config)
   answer = generator.generate(prompt)
   json_data = generator.generate_json(prompt, schema)
   ```

2. **EmbeddingGenerator** - Embedding 生成
   ```python
   embedder = EmbeddingGenerator.from_config(config)
   embedding = embedder.generate("text")
   embeddings = embedder.generate_batch(["text1", "text2"])
   ```

3. **ProgressBar** - 进度显示
   ```python
   progress = ProgressBar(total=100, desc="Processing")
   progress.update(current=50, status="Running...")
   ```

#### 2.5.2 tools 辅助工具

目录: `tools/`

```
tools/
├── config_validator.py             # 配置文件验证
├── config_migration.py             # 配置迁移工具
└── calculate_combinations.py       # 组合数计算
```

**使用场景**:
- **config_validator**: 检查配置文件完整性
- **config_migration**: 升级旧版本配置
- **calculate_combinations**: 计算实验组合数（用于规划实验）

---

## 3. evaluation 模块

结果评估模块用于分析实验输出，生成图表和报告。

### 3.1 目录结构

```
evaluation/
├── README.md                       # 评估模块说明
└── specialized_analysis/           # 专项分析脚本
    ├── README.md                   # 分析脚本说明
    ├── run_locomo_f1_analysis.py   # F1 分数分析
    ├── run_locomo_cross_method_analysis.py  # 跨方法对比
    ├── run_conflict_resolution_subem_analysis.py  # SubEM 分析
    ├── run_tim_strategy_round_analysis.py  # TiM 策略分析
    ├── pangu_plot_category_bar_chart.py    # 类别柱状图
    └── pangu_plot_category_round_progression.py  # 类别进展图
```

### 3.2 分析类型

| 脚本 | 分析内容 | 输入 | 输出 |
|------|----------|------|------|
| `run_locomo_f1_analysis.py` | Token-based F1 分数趋势 | 结果 JSON | F1 曲线图 |
| `run_locomo_cross_method_analysis.py` | 多算法对比 | 多个结果目录 | 对比表格、热力图 |
| `pangu_plot_category_bar_chart.py` | 五类问题准确率对比 | 结果 JSON | 柱状图 |
| `pangu_plot_category_round_progression.py` | 随轮次变化的准确率 | 结果 JSON | 折线图 |

### 3.3 评估指标

当前支持的指标：

| 指标 | 计算方法 | 适用场景 |
|------|----------|----------|
| **Token-based F1** | 基于词级别的精确率和召回率 | 生成类问题 |
| **Exact Match (EM)** | 答案完全一致 | 事实类问题 |
| **Category Accuracy** | 各类别问题的准确率 | LoCoMo 数据集 |

---

## 4. 数据流与执行流程

### 4.1 完整数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          数据流全景图                                    │
└─────────────────────────────────────────────────────────────────────────┘

[1] MemorySource 输出
    ↓
    {
      packet_idx: 0,
      dialogs: [{role: "user", content: "..."}],
      visible_questions: [...]
    }
    ↓
[2] PipelineCaller 判断
    ↓
    ├─→ [需要插入] → 调用 memory_insert_service
    │   ↓
    │   PreInsert (action="extract")
    │   ↓
    │   {
    │     memory_entries: [
    │       {text: "事实1", embedding: [...], metadata: {...}},
    │       {text: "事实2", embedding: [...], metadata: {...}}
    │     ]
    │   }
    │   ↓
    │   MemoryInsert
    │   ↓
    │   {
    │     insert_stats: {inserted: 2, failed: 0, entry_ids: ["id1", "id2"]}
    │   }
    │   ↓
    │   PostInsert (action="summarize")
    │   ↓
    │   返回 PipelineCaller
    │
    └─→ [需要测试] → 调用 memory_test_service（对每个问题）
        ↓
        PreRetrieval (action="none")
        ↓
        {
          question: "用户叫什么名字？",
          query_embedding: [...]
        }
        ↓
        MemoryRetrieval
        ↓
        {
          memory_data: [
            {"text": "用户名字是张三", "score": 0.95},
            {"text": "用户年龄25岁", "score": 0.82}
          ],
          retrieval_stats: {retrieved: 2, time_ms: 15.3}
        }
        ↓
        PostRetrieval (action="none" - 格式化对话历史)
        ↓
        {
          history_text: "User: ...\nAssistant: ...\n..."
        }
        ↓
        MemoryEvaluation (使用 LLM 生成答案)
        ↓
        {
          answer: "张三",
          generation_time_ms: 234.5
        }
        ↓
        返回 PipelineCaller
        ↓
[3] PipelineCaller 聚合测试结果
    ↓
    {
      test_results: {
        "问题1": {"answer": "张三", "ground_truth": "张三", "correct": true},
        "问题2": {"answer": "25岁", "ground_truth": "25", "correct": false}
      },
      test_round_idx: 1,
      accuracy: 0.5
    }
    ↓
[4] MemorySink 收集并保存
    ↓
    results.json
```

### 4.2 测试触发机制

PipelineCaller 采用 **问题驱动的测试策略**:

```python
# 计算测试阈值（例如：每 100 个问题测试一次）
test_thresholds = calculate_test_thresholds(
    total_questions=1000,
    test_segments=10
)
# 结果: [100, 200, 300, ..., 1000]

# 判断是否需要测试
current_question_count = 150
if current_question_count >= test_thresholds[next_test_idx]:
    # 触发测试
    test_all_visible_questions()
```

**不同数据集的测试策略**:
- **LoCoMo**: 每 100 个问题测试一次（可配置 `test_segments`）
- **Conflict Resolution**: 每 455 个事实测试一次（固定间隔）
- **LongMemEval**: 自定义测试点

---

## 5. 扩展开发指南

### 5.1 添加新的 PreInsert Action

1. **创建 Action 文件**: `libs/pre_insert/my_action/my_action.py`

```python
from benchmarks.experiment.libs.pre_insert.base import BasePreInsertAction, MemoryEntry

class MyAction(BasePreInsertAction):
    """自定义预处理策略"""

    def __init__(self, config):
        super().__init__(config)
        # 初始化工具（如 LLM）

    def execute(self, input_data: PreInsertInput) -> list[MemoryEntry]:
        """执行预处理

        Args:
            input_data: 包含 dialogs, session_id 等

        Returns:
            list[MemoryEntry]: 记忆条目列表
        """
        # 实现逻辑
        return [
            MemoryEntry(
                text="处理后的文本",
                embedding=None,  # 可选
                metadata={"custom_key": "value"}
            )
        ]
```

2. **注册 Action**: 在 `libs/pre_insert/__init__.py` 中注册

```python
from .registry import PreInsertActionRegistry
from .my_action.my_action import MyAction

PreInsertActionRegistry.register("my_action", MyAction)
```

3. **更新配置模板**: 在 `config/template_full.yaml` 中添加

```yaml
operators:
  pre_insert:
    action: "my_action"
    my_action_param1: "value1"
```

### 5.2 添加新的记忆服务

1. **实现服务类**: 在 `sage/neuromem/services/` 中创建

```python
from sage.neuromem.services.base_service import BaseMemoryService

class MyMemoryService(BaseMemoryService):
    def __init__(self, collection, config):
        super().__init__(collection, config)

    def insert(self, data_id: str, data: dict) -> bool:
        # 实现插入逻辑
        pass

    def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        # 实现检索逻辑
        pass
```

2. **注册服务**: 使用装饰器

```python
from sage.neuromem.services import MemoryServiceRegistry

@MemoryServiceRegistry.register("my_service")
class MyMemoryService(BaseMemoryService):
    ...
```

3. **创建配置文件**: 在 `config/` 中添加

```yaml
services:
  services_type: "partitional.my_service"
  my_service:
    param1: "value1"
    param2: 100
```

### 5.3 支持新数据集

1. **创建 DataLoader**: 在 `sage/data/sources/` 中实现

```python
class MyDataLoader:
    def get_turn(self, task_id: str):
        """返回会话结构: [(session_id, max_dialog_idx), ...]"""
        pass

    def load_dialog(self, task_id: str, session_id: str, dialog_idx: int):
        """加载单个对话"""
        pass

    def get_total_valid_questions(self, task_id: str):
        """返回总问题数"""
        pass

    def get_questions_by_round(self, task_id: str, round_num: int):
        """返回指定轮次的问题"""
        pass
```

2. **在 MemorySource 中注册**:

```python
class MemorySource(BatchFunction):
    def __init__(self, config):
        dataset = config.get("dataset")
        if dataset == "my_dataset":
            self.loader = MyDataLoader()
        ...
```

3. **更新 PipelineCaller**:

```python
class PipelineCaller(MapFunction):
    def __init__(self, config):
        dataset = config.get("dataset")
        if dataset == "my_dataset":
            self.loader = MyDataLoader()
        ...
```

---

## 6. 最佳实践

### 6.1 配置管理

✅ **推荐**:
- 使用 `template_full.yaml` 作为基础，复制后修改
- 配置文件命名规范: `{dataset}_{algorithm}_pipeline.yaml`
- 所有 Prompt 集中在配置文件中，便于调优

❌ **避免**:
- 硬编码参数在代码中
- 修改 `template_full.yaml` 本身（保持模板完整性）

### 6.2 日志与调试

✅ **推荐**:
- 使用 `CustomLogger` 而非 `print()`
- 设置 `memory_insert_verbose: true` 调试插入问题
- 设置 `memory_test_verbose: true` 调试检索问题
- 查看日志文件定位错误: `.sage/output/benchmarks/.../*.log`

### 6.3 性能优化

✅ **推荐**:
- 使用 `EmbeddingGenerator.generate_batch()` 批量生成向量
- 设置合理的 `test_segments` 避免过于频繁的测试
- 使用 GPU 加速向量检索（FAISS）

### 6.4 代码规范

✅ **推荐**:
- 遵循项目的 Copilot Instructions 规范
- Action 类保持 < 200 行，职责单一
- 添加详细的 Docstring（中文）
- 更新对应的 README 文档

### 6.5 测试与验证

✅ **推荐**:
- 新增 Action 后运行单元测试: `pytest tests/unit/`
- 使用小数据集（如 `conv-26`）快速验证
- 对比不同配置的结果 JSON，确保改动符合预期

---

## 附录

### A. 常见问题

**Q1: 如何添加新的 LLM 后端？**

A: 修改 `utils/llm/llm_generator.py`，添加新的 API 调用逻辑，通过配置文件的 `base_url` 和 `model_name` 切换。

**Q2: 如何修改测试频率？**

A: 调整配置文件中的 `runtime.test_segments` 参数。

**Q3: 如何支持多种 Embedding 模型？**

A: 修改 `utils/llm/embedding_generator.py`，添加新的 Embedding 提供商。

**Q4: Pipeline 超时怎么办？**

A: 增加 `runtime.pipeline_service_timeout` 和 `runtime.service_timeout` 参数（秒）。

### B. 相关文档

- [NeuroMem 主文档](../docs/README.md)
- [Services API Reference](../docs/services/API_REFERENCE.md)
- [配置迁移指南](../docs/NAMESPACE_MIGRATION_GUIDE.md)
- [Evaluation 模块说明](./evaluation/README.md)

---

**文档维护**: 如修改代码结构，请同步更新本文档。
