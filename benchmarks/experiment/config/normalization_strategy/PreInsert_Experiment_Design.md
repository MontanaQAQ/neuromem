# PreRetrieval 查询形塑实验设计

> 基于 Dev_Archive.md 中已复现的代表性工作，针对三个记忆体结构设计 PreRetrieval 阶段的对比实验
>
> 目标：在不同记忆体架构下，评估查询优化策略对检索准确率的影响
>
> 实验范围：PreRetrieval 阶段（难度★☆☆☆☆），固定其他阶段为 baseline 配置
_____________________________________________________________________

# PreInsert 归一化策略实验设计

> 基于 Dev_Archive.md 中已复现的代表性工作，围绕“插入前归一化（PreInsert）”算子的三类方案（none/enrich/rewrite）设计系统化对比实验。
>
> 目标：在不同记忆体架构下，比较三类 PreInsert 算子对“插入质量、后续检索准确率与效率”的综合影响，寻找最优算子与参数组合。
>
> 实验范围：PreInsert 阶段（难度★★☆☆☆），固定其他阶段为 baseline 配置。

______________________________________________________________________

## 📋 PreInsert 算子分类体系（三类）

本实验采用与代码实现一致的三类算子体系（参考 `benchmarks/experiment/libs/pre_insert`）：

| 类别                 | action 前缀       | 子算子示例                             | 功能定位                                     | 适用场景                         |
| -------------------- | ----------------- | -------------------------------------- | -------------------------------------------- | -------------------------------- |
| **1. 无处理**        | `none`            | `none`                                 | 透传原始内容，不做任何归一化                 | 作为基准线/排除副作用           |
| **2. 增润（Enrich）**| `enrich.*`        | `keyword`、`summarize`、`entity`                | 保持或轻量变更 text，并在 metadata 中附加结构化信息 | 标签/摘要/实体增润与混合检索 |
| **3. 重写（Rewrite）**| `rewrite.*`       | `compress`、`fact_extract`、`triplet_extract`   | 对 text 进行规整/摘要/净化，必要时生成更细粒度文本 | 长文本分段压缩、事实/三元组重写 |

设计原则：

- 功能正交，三类算子分别针对“是否处理/结构变换/语义抽取”。
- 层次递进，支持按类别或组合（变换→抽取）构建流水线，但本实验以“单类为主”的主效应对比为核心，组合作为扩展实验。

______________________________________________________________________

## ⚠️ 重要架构约束（插入侧）

不同记忆体结构对 PreInsert 的可用性与收益存在差异：

| 记忆体结构                         | 插入约束与建议                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **TiM** (vector_memory / hash)     | 向量检索对片段边界与语义密度敏感，推荐使用 `rewrite.compress` 控制片段长度与语义密度；`rewrite.triplet_extract` 适用于结构化检索协同。 |
| **MemoryOS** (hierarchical_memory) | 分层容量与主动迁移策略需谨慎调参；过度摘要可能损失细节。               |
| **Mem0ᵍ** (hybrid graph)           | 图场景中 `extract.entity/triple/fact` 直接提升可图化程度。                     |

实验影响：

- 作为统一 baseline，提供 `none`（透传）以衡量副作用；在长文本/噪声较多的场景推荐提供 `rewrite.compress` 作为稳健基线。
- 组合流水线可能更优，但主实验先比较四类“单算子”主效应，再在扩展实验中评估二/三步组合。

______________________________________________________________________

## 1. 三个代表性记忆体结构选取（同 PreRetrieval）

沿用已复现的三种结构：TiM、MemoryOS、Mem0ᵍ。服务与运行时固定项与 PreRetrieval 一致，此处不再赘述。

______________________________________________________________________

## 2. PreInsert 策略候选水平（TiM 系列示例）

针对 TiM，选取三类算子各一个具代表性的子算子作为主效应对比：

### 2.1 Baseline：`none`

- 配置文件：`TiM_locomo_none_pre_insert_pipeline.yaml`
- 内存名称：`PreInsert_TiM_none`
- 操作：不做处理，原文直接入库（向量化在插入服务侧完成）。
- 配置：

```yaml
pre_insert:
  action: "none"
```

### 2.2 重写：`rewrite.compress`

- 配置文件：`TiM_locomo_rewrite_compress_pre_insert_pipeline.yaml`
- 内存名称：`PreInsert_TiM_rewrite_compress`
- 操作：语义分段与压缩去噪（SeCom），控制每段长度与冗余，保持事实完整。
- 关键参数（建议搜索域）：
  - `min_segment_size`: [100, 200, 300]
  - `max_segment_size`: [300, 500, 700]
  - `transform_type`: ["topic_segment"]
  配置：

```yaml
pre_insert:
  action: "rewrite.compress"
  transform_type: "topic_segment"
  min_segment_size: 100
  max_segment_size: 500
```

### 2.3 语义抽取：`rewrite.triplet_extract`

- 配置文件：`TiM_locomo_rewrite_triplet_extract_pre_insert_pipeline.yaml`
- 内存名称：`PreInsert_TiM_rewrite_triplet_extract`
- 操作：从文本抽取三元组，按结构化单元入库（可选择保留原文）。
- 关键参数：
  - `extraction_method`: ["llm", "rule"]
  - `max_triplets`: [5, 10, 20]
  - `keep_original`: [true, false]
- 配置：

```yaml
pre_insert:
  action: "rewrite.triplet_extract"
  extraction_method: "llm"
  max_triplets: 10
  keep_original: false
```



______________________________________________________________________

## 3. TiM 实验设计矩阵（三个主效应配置）

| 配置ID | 配置文件                                       | 内存名称                 | PreInsert 算子             | 预期假设                                                         |
| ------ | ---------------------------------------------- | ------------------------ | -------------------------- | ---------------------------------------------------------------- |
| **P1** | `TiM_locomo_none_pre_insert_pipeline.yaml`     | `PreInsert_TiM_none`                | `none`                     | 作为插入侧基线，便于衡量各类算子的真实增益与副作用               |
| **P2** | `TiM_locomo_rewrite_compress_pre_insert_pipeline.yaml` | `PreInsert_TiM_rewrite_compress`    | `rewrite.compress`         | 控制片段长度与压缩冗余可提升后续向量检索的稳定性，降低重复与噪声 |
| **P3** | `TiM_locomo_rewrite_triplet_extract_pre_insert_pipeline.yaml`  | `PreInsert_TiM_rewrite_triplet_extract` | `rewrite.triplet_extract`  | 结构化单元更易被知识对齐与图召回，复杂查询的准确率更高           |

对比维度：

- 基线 vs 处理：P1 vs P2/P3
- 压缩重写 vs 语义重写：P2 vs P3

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

统计分析：采用配对t检验/单因素方差分析（P1–P3），并报告效应量（Cohen's d）。

______________________________________________________________________

## 5. 配置文件命名规范

```
pre_insert_<memory_structure>_<strategy>.yaml

例如：
- pre_insert_tim_none.yaml
- pre_insert_tim_rewrite_compress.yaml
- pre_insert_tim_rewrite_triplet_extract.yaml
```

______________________________________________________________________

## 6. 预期实验结果假设

- 长文本/噪声场景下，`rewrite.compress` 将显著提升检索稳定性与准确率（优于 P1）。
- 结构化任务/图检索场景，`rewrite.triplet_extract` 会在复杂查询上带来更高的 End-to-End 准确率（优于 P2）。
- 过度摘要（`enrich.summarize` 的高压缩比）可能导致细节损失，准确率下降；因此作为扩展实验评估。

______________________________________________________________________

## 7. 扩展实验：两步/三步组合流水线

在主效应对比后，评估组合策略以验证协同增益：

### 7.1 组合：`enrich.summarize` → `enrich.keyword`

目标：在容量受限场景将信息压缩成关键词。

评估方式：对比与单算子（P2/P3）以及基线（P1）的差异；记录插入开销与检索收益的性价比。

______________________________________________________________________

## 8. 边界与鲁棒性测试

- 极短文本（<64 tokens）：直接使用 `none` 或 `enrich.keyword`。
- 超长文本（>4096 tokens）：优先使用 `rewrite.compress` 控制片段长度与过度冗余，避免跨片段语义断裂。
- 噪声/格式混杂：启用 `rewrite.compress`；对表格/列表型内容，建议保留原文与抽取并行。
- 权限/容量受限：通过调整插入过滤策略与容量阈值控制入库规模。

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
