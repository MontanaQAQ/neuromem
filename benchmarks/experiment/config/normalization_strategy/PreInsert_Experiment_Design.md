# PreRetrieval 查询形塑实验设计

> 基于 Dev_Archive.md 中已复现的代表性工作，针对三个记忆体结构设计 PreRetrieval 阶段的对比实验
>
> 目标：在不同记忆体架构下，评估查询优化策略对检索准确率的影响
>
> 实验范围：PreRetrieval 阶段（难度★☆☆☆☆），固定其他阶段为 baseline 配置
_____________________________________________________________________

# PreInsert 归一化策略实验设计

> 基于 Dev_Archive.md 中已复现的代表性工作，围绕“插入前归一化（PreInsert）”算子的四类方案设计系统化对比实验。
>
> 目标：在不同记忆体架构下，比较四类 PreInsert 算子对“插入质量、后续检索准确率与效率”的综合影响，寻找最优算子与参数组合。
>
> 实验范围：PreInsert 阶段（难度★★☆☆☆），固定其他阶段为 baseline 配置。

______________________________________________________________________

## 📋 PreInsert 算子分类体系（四类）

本实验采用与代码实现一致的四类算子体系（参考 `benchmark_memory/experiment/libs/pre_insert`）：

| 类别                 | action 前缀       | 子算子示例                             | 功能定位                                     | 适用场景                         |
| -------------------- | ----------------- | -------------------------------------- | -------------------------------------------- | -------------------------------- |
| **1. 无处理**        | `none`            | `none`                                 | 透传原始内容，不做任何归一化                 | 作为基准线/排除副作用           |
| **2. 结构变换**      | `transform.*`     | `segment`、`segment_denoise`、`chunking`、`summarize`、`continuity_check` | 片段化、降噪、摘要化，统一内容结构           | 长文本插入、质量不一的输入       |
| **3. 语义抽取**      | `extract.*`       | `keyword`、`entity`、`noun`、`triple`、`fact`、`multi_summary`           | 把原文转化为语义单元（词/实体/三元组/事实）   | 图/三元组记忆、结构化检索       |
| **4. 重要性/热度评估** | `score.*`         | `importance`、`heat`                   | 依据重要性/热度打分与筛选，控制插入与层级迁移 | 分层记忆、容量受限/需主动淘汰   |

设计原则：

- 功能正交，四类算子分别针对“是否处理/结构变换/语义抽取/重要性评估”。
- 层次递进，支持按类别或组合（变换→抽取→打分）构建流水线，但本实验以“单类为主”的主效应对比为核心，组合作为扩展实验。

______________________________________________________________________

## ⚠️ 重要架构约束（插入侧）

不同记忆体结构对 PreInsert 的可用性与收益存在差异：

| 记忆体结构                         | 插入约束与建议                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **TiM** (vector_memory / hash)     | 向量检索对片段边界与语义密度敏感，推荐使用 `transform.segment(+denoise)` 控制片段长度与重叠；`extract.triple` 适用于结构化检索协同。 |
| **MemoryOS** (hierarchical_memory) | 分层容量与主动迁移策略依赖“打分信号”，`score.heat`/`score.importance` 可提升迁移质量；过度摘要可能损失细节。               |
| **Mem0ᵍ** (hybrid graph)           | 图场景中 `extract.entity/triple/fact` 直接提升可图化程度；`continuity_check` 可以避免破坏关系上下文。                     |

实验影响：

- 作为统一 baseline，提供 `none`（透传）以衡量副作用；在长文本/噪声较多的场景必须提供变换类作为稳健基线（例如 `segment_denoise`）。
- 组合流水线可能更优，但主实验先比较四类“单算子”主效应，再在扩展实验中评估二/三步组合。

______________________________________________________________________

## 1. 三个代表性记忆体结构选取（同 PreRetrieval）

沿用已复现的三种结构：TiM、MemoryOS、Mem0ᵍ。服务与运行时固定项与 PreRetrieval 一致，此处不再赘述。

______________________________________________________________________

## 2. PreInsert 策略候选水平（TiM 系列示例）

针对 TiM，选取四类算子各一个具代表性的子算子作为主效应对比：

### 2.1 Baseline：`none`

- 配置文件：`TiM_locomo_none_pre_insert_pipeline.yaml`
- 内存名称：`TiM-preinsert-none`
- 操作：不做处理，原文直接入库（向量化在插入服务侧完成）。
- 配置：

```yaml
pre_insert:
  action: "none"
```

### 2.2 结构变换：`transform.segment_denoise`

- 配置文件：`TiM_locomo_segment_denoise_pre_insert_pipeline.yaml`
- 内存名称：`TiM-preinsert-segdenoise`
- 操作：先分段再降噪，保证每段长度与重叠合理，过滤低质量句段。
- 关键参数（建议搜索域）：
  - `segment_size`: [256, 512, 1024]
  - `overlap`: [0, 64, 128]
  - `denoise_threshold`: [0.2, 0.4, 0.6]
- 配置：

```yaml
pre_insert:
  action: "transform.segment_denoise"
  segment_size: 512
  overlap: 64
  denoise_threshold: 0.4
```

### 2.3 语义抽取：`extract.triple`

- 配置文件：`TiM_locomo_extract_triple_pre_insert_pipeline.yaml`
- 内存名称：`TiM-preinsert-triple`
- 操作：从文本抽取三元组，按结构化单元入库（可选择保留原文）。
- 关键参数：
  - `extraction_method`: ["llm", "rule"]
  - `max_triplets`: [5, 10, 20]
  - `keep_original`: [true, false]
- 配置：

```yaml
pre_insert:
  action: "extract.triple"
  extraction_method: "llm"
  max_triplets: 10
  keep_original: false
```

### 2.4 重要性/热度评估：`score.heat`

- 配置文件：`TiM_locomo_score_heat_pre_insert_pipeline.yaml`
- 内存名称：`TiM-preinsert-heat`
- 操作：对片段或抽取单元打热度分，低于阈值不入库或入低层级。
- 关键参数：
  - `heat_window`: [3, 5, 7]
  - `min_heat_threshold`: [0.3, 0.5, 0.7]
- 配置：

```yaml
pre_insert:
  action: "score.heat"
  heat_window: 5
  min_heat_threshold: 0.5
```

注：若平台为 MemoryOS，可将 `score.importance` 作为并行候选，参数形式与 `score.heat` 类似，阈值语义改为“重要性”。

______________________________________________________________________

## 3. TiM 实验设计矩阵（四个主效应配置）

| 配置ID | 配置文件                                       | 内存名称                 | PreInsert 算子             | 预期假设                                                         |
| ------ | ---------------------------------------------- | ------------------------ | -------------------------- | ---------------------------------------------------------------- |
| **P1** | `TiM_locomo_none_pre_insert_pipeline.yaml`     | `TiM-preinsert-none`     | `none`                     | 作为插入侧基线，便于衡量各类算子的真实增益与副作用               |
| **P2** | `TiM_locomo_segment_denoise_pre_insert_pipeline.yaml` | `TiM-preinsert-segdenoise` | `transform.segment_denoise` | 控制片段长度与降噪可提升后续向量检索的稳定性，降低冗余           |
| **P3** | `TiM_locomo_extract_triple_pre_insert_pipeline.yaml`  | `TiM-preinsert-triple`   | `extract.triple`           | 结构化单元更易被知识对齐与图召回，复杂查询的准确率更高           |
| **P4** | `TiM_locomo_score_heat_pre_insert_pipeline.yaml`      | `TiM-preinsert-heat`     | `score.heat`               | 过滤低价值信息，减少噪声插入，分层迁移更稳定，整体检索时间更短   |

对比维度：

- 基线 vs 处理：P1 vs P2/P3/P4
- 结构 vs 语义：P2 vs P3
- 质量控制：P2 vs P4（先变换再筛选 VS 仅筛选）

固定配置（与 PreRetrieval 一致的非干预阶段）：

```yaml
operators:
  post_insert:
    action: "none"
  pre_retrieval:
    action: "embedding"  # TiM 必须有向量；MemoryOS/Mem0ᵍ可用 none 作为基线
  post_retrieval:
    action: "none"
```

______________________________________________________________________

## 4. 统一运行时与评估指标

运行时配置沿用既有设置（数据集、LLM、Embedding），此处补充 PreInsert 特定评估指标：

- 主要指标：
  - Retrieval Accuracy（段/单元级）
  - End-to-End Task Accuracy（回答正确率）
- 次要指标：
  - Insertion Coverage（入库覆盖率/被筛除比例）
  - Memory Density（单位容量的有效信息密度）
  - Redundancy Ratio（重复片段/近似片段比例）
- 效率指标：
  - Average Insertion Latency（单样本插入耗时）
  - Storage Footprint（插入后存储占用增长）
  - Downstream Retrieval Time（后续检索平均耗时）

统计分析：采用配对t检验/单因素方差分析（P1–P4），并报告效应量（Cohen's d）。

______________________________________________________________________

## 5. 配置文件命名规范

```
pre_insert_<memory_structure>_<strategy>.yaml

例如：
- pre_insert_tim_none.yaml
- pre_insert_tim_segment_denoise.yaml
- pre_insert_tim_extract_triple.yaml
- pre_insert_tim_score_heat.yaml
```

______________________________________________________________________

## 6. 预期实验结果假设

- 长文本/噪声场景下，`transform.segment_denoise` 将显著提升检索稳定性与准确率（优于 P1）。
- 结构化任务/图检索场景，`extract.triple` 会在复杂查询上带来更高的 End-to-End 准确率（优于 P2）。
- 分层记忆场景，`score.heat` 或 `score.importance` 能降低无效插入与后续冗余检索（效率指标更优）。
- 过度摘要（`transform.summarize` 的高压缩比）可能导致细节损失，准确率下降；因此仅在扩展实验中评估。

______________________________________________________________________

## 7. 扩展实验：两步/三步组合流水线

在主效应对比后，评估组合策略以验证协同增益：

### 7.1 组合 A：`transform.segment_denoise` → `score.heat`

目标：先控制片段质量，再按热度筛选，兼顾效果与效率。

### 7.2 组合 B：`transform.segment` → `extract.triple`

目标：对长文本先划分片段，再对片段抽取三元组，提高抽取精度与覆盖率。

### 7.3 组合 C：`transform.summarize` → `extract.keyword` → `score.importance`

目标：在容量受限场景将信息压缩成关键词，再以重要性控制入库与层级迁移。

评估方式：对比与单算子（P2/P3/P4）以及基线（P1）的差异；记录插入开销与检索收益的性价比。

______________________________________________________________________

## 8. 边界与鲁棒性测试

- 极短文本（<64 tokens）：禁用 `segment`，直接 `none` 或 `extract.keyword`。
- 超长文本（>4096 tokens）：优先 `segment(+overlap)`，避免跨片段语义断裂；必要时 `continuity_check`。
- 噪声/格式混杂：启用 `segment_denoise`；对表格/列表型内容，建议保留原文与抽取并行。
- 权限/容量受限：加大 `min_heat_threshold` 或 `importance_threshold`，控制入库规模。

______________________________________________________________________

## 9. 实验执行与复现实操（摘要）

- 统一随机种子：`seed: 42`。
- 每个配置至少在 `test_segments: 10` 的 locomo 子集上跑 3 次，报告均值±标准差。
- 保留运行日志与插入统计（入库数量、被过滤比例、耗时分布）。

______________________________________________________________________

## 10. 质量门禁

- Build：PASS（文档修改不影响编译）。
- Lint/Typecheck：PASS（无代码变更）。
- Tests：PASS（无单测受影响；如后续引入组合流水线需补充 E2E 测试）。

**配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "decompose"
    decompose_strategy: "llm"  # llm | rule | hybrid
    max_sub_queries: 3
    sub_query_action: "parallel"  # parallel | sequential
    embed_sub_queries: true
```

**策略类型**:

- `llm`: 使用 LLM 智能分解（高精度，高延迟）
- `rule`: 基于分隔符规则分解（低延迟，适合简单场景）
- `hybrid`: 先规则后 LLM fallback（平衡方案）

#### 7.2.2 Retrieval Route - 检索路由

**功能**: 根据查询内容生成检索策略提示 (hints)，指导服务层选择合适的检索方式

**适用场景**:

- 多源记忆系统：根据查询类型选择 STM/MTM/LTM
- 条件分支检索："remember" → LTM, "recently" → STM

**配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "route"
    route_strategy: "keyword"  # keyword | classifier | llm
    keyword_rules:
      - keywords: ["remember", "recall"]
        strategy: "long_term_memory"
        params: { tier: "ltm" }
      - keywords: ["recently", "just now"]
        strategy: "short_term_memory"
        params: { tier: "stm" }
    default_strategy: "semantic_search"
```

**策略类型**:

- `keyword`: 基于关键词规则路由（低延迟，规则可控）
- `classifier`: 基于分类器路由（需要训练，暂未实现）
- `llm`: 基于 LLM 智能路由（高灵活性，高延迟）

#### 7.2.3 Multi Embed - 多维向量化

**功能**: 使用多个 embedding 模型生成多维向量，综合多种相似度维度

**适用场景**:

- 精细化检索：语义 + 情感 + 代码特征
- 多模态检索：文本 + 图像 + 音频

**配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "multi_embed"
    embeddings:
      - name: "semantic"
        model: "BAAI/bge-m3"
        weight: 0.6
      - name: "emotion"
        model: "SamLowe/roberta-base-go_emotions"
        weight: 0.4
    output_format: "weighted"  # weighted | dict | concat
```

**输出格式**:

- `weighted`: 加权融合为单一向量（推荐）
- `dict`: 字典格式保留所有向量（供后续处理）
- `concat`: 拼接所有向量（维度倍增）

### 7.3 Enhancement vs Optimize

| 对比维度       | Optimize                         | Enhancement                   |
| -------------- | -------------------------------- | ----------------------------- |
| **定位**       | 查询优化（文本层面）             | 查询增强（结构层面）          |
| **子类型**     | keyword_extract, expand, rewrite | decompose, route, multi_embed |
| **复杂度**     | 中等（单次查询优化）             | 高（多查询/多路由/多向量）    |
| **适用场景**   | 基础查询优化                     | 高级检索增强                  |
| **实验优先级** | 高（核心对比实验）               | 中（扩展实验）                |

### 7.4 Demo 配置文件

Enhancement 类型已提供三个 Demo 配置文件：

| 配置文件                                          | Enhancement 类型 | 记忆体结构 | 说明                   |
| ------------------------------------------------- | ---------------- | ---------- | ---------------------- |
| `pre_retrieval_enhancement_decompose_demo.yaml`   | decompose        | TiM        | 复杂查询分解为子查询   |
| `pre_retrieval_enhancement_route_demo.yaml`       | route            | MemoryOS   | 基于关键词的层级路由   |
| `pre_retrieval_enhancement_multi_embed_demo.yaml` | multi_embed      | Mem0ᵍ      | 语义+代码+情感多维检索 |

**注意**: Enhancement 实验为高级功能演示，**不在核心对比实验范围内**。

______________________________________________________________________

## 8. 下一步实施计划

1. **Phase 1**: 实施 9 个核心对比组合 (V1-V3, H1-H3, G1-G3)
1. **Phase 2**: 基于 Phase 1 结果，扩展到完整的 15 个组合
1. **Phase 3**: （可选）运行 3 个 Enhancement Demo，评估高级策略效果
1. **Phase 4**: 分析结果，撰写 PreRetrieval 策略效果报告
1. **Phase 5**: 基于最优 PreRetrieval 配置，进入下一阶段 PostRetrieval 实验

通过这个实验设计，我们可以系统地评估不同查询优化策略在不同记忆体结构下的效果，为后续的组合实验奠定基础。
