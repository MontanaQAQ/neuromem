# PostRetrieval 后处理算子库

> **模块路径**: `benchmarks/experiment/libs/post_retrieval/`  
> **设计理念**: 策略模式 + 论文驱动 + 数据结构无关  
> **版本**: v1.0 (2026-01-13)

---

## ? 目录

- [一、快速开始](#一快速开始)
- [二、分类体系](#二分类体系)
- [三、算子清单](#三算子清单)
- [四、使用指南](#四使用指南)
- [五、论文映射](#五论文映射)
- [六、扩展开发](#六扩展开发)

---

## 一、快速开始

### 1.1 核心概念

**PostRetrieval** 是记忆检索后的后处理阶段，对检索结果进行：
- **重排序** (Rerank): 调整结果顺序
- **过滤** (Filter): 减少结果数量
- **合并** (Merge): 整合多次检索
- **增强** (Augment): 添加额外信息

### 1.2 配置示例

```yaml
# config/xxx_pipeline.yaml
operators:
  post_retrieval:
    action: "rerank"              # 选择操作类型
    rerank_type: "time_weighted"  # 选择具体算子

    # 算子参数
    time_decay_rate: 0.1
    enable_reinforcement: true
```

### 1.3 代码示例

```python
from benchmarks.experiment.libs.post_retrieval import PostRetrieval

# 创建算子
config = {
    "operators.post_retrieval": {
        "action": "rerank",
        "rerank_type": "time_weighted",
        "time_decay_rate": 0.1
    }
}
operator = PostRetrieval(config)

# 执行后处理
data = {
    "memory_data": [...],  # 检索结果
    "question": "今天天气怎么样？"
}
result = operator.execute(data)
```

---

## 二、分类体系

### 2.1 分类依据

按照**对检索结果的操作类型**分为四大类：

```
post_retrieval/
├── rerank/      # 重排序 - 调整结果顺序
├── filter/      # 过滤 - 减少结果数量
├── merge/       # 合并 - 整合多次检索
└── augment/     # 增强 - 添加额外信息
```

### 2.2 操作特征对比

| 类别 | 输入→输出 | 数量变化 | 顺序变化 | 内容变化 | 多次检索 |
|------|----------|---------|---------|---------|---------|
| **Rerank** | [A,B,C] → [C,A,B] | ? 不变 | ? 改变 | ? 不变 | ? 单次 |
| **Filter** | [A,B,C] → [A,B] | ? 减少 | ? 不变 | ? 不变 | ? 单次 |
| **Merge** | [A,B]+[B,C] → [A,B,C] | ? 增加 | ? 改变 | ? 不变 | ? 多次 |
| **Augment** | [{text}] → [{text,ctx}] | ? 不变 | ? 不变 | ? 修改 | ? 单次 |

### 2.3 决策树

```
检索到N个结果后...
  |
  ├─ 需要调整顺序？ → Rerank
  ├─ 需要减少数量？ → Filter
  ├─ 需要整合多次检索？ → Merge
  └─ 需要添加额外信息？ → Augment
```

---

## 三、算子清单

### 3.1 Rerank (重排序) - 4个

| 算子 | 注册名 | 论文 | 核心逻辑 | 适配结构 |
|-----|--------|-----|---------|---------|
| SemanticRerankAction | `rerank.semantic` | 通用 | LLM语义理解 | 所有 |
| TimeWeightedRerankAction | `rerank.time_weighted` | MemoryBank | $e^{-\lambda t}$ | 分层/分区 |
| PPRRerankAction | `rerank.ppr` | HippoRAG | PageRank图遍历 | 图 |
| WeightedRerankAction | `rerank.weighted` | LD-Agent | 多因子加权 | 分层 |

### 3.2 Filter (过滤) - 3个

| 算子 | 注册名 | 论文 | 核心逻辑 | 适配结构 |
|-----|--------|-----|---------|---------|
| TopKFilterAction | `filter.top_k` | 通用 | 保留前K个 | 所有 |
| ThresholdFilterAction | `filter.threshold` | Mem0 | 分数阈值 | 所有 |
| TokenBudgetFilterAction | `filter.token_budget` | SCM | Token预算 | 所有 |

### 3.3 Merge (合并) - 4个

| 算子 | 注册名 | 论文 | 核心逻辑 | 适配结构 |
|-----|--------|-----|---------|---------|
| MultiQueryMergeAction | `merge.multi_query` | MemoryOS | Union/Intersection | 分层 |
| MultiTierMergeAction | `merge.multi_tier` | MemGPT | RRF融合 | 分层 |
| LinkExpandMergeAction | `merge.link_expand` | A-Mem | 邻居扩展 | 图 |
| SCMThreeWayMergeAction | `scm_three_way` | SCM | Drop/Summary/Raw | 分区 |

### 3.4 Augment (增强) - 2个

| 算子 | 注册名 | 论文 | 核心逻辑 | 适配结构 |
|-----|--------|-----|---------|---------|
| AugmentAction | `augment` | MemoryOS | 添加上下文 | 分层 |
| ReinforceAction | `augment.reinforce` | MemoryBank | 更新强度 | 分层/分区 |

**总计**: 13个算子

---

## 四、使用指南

### 4.1 配置模板

#### Rerank 配置

```yaml
operators:
  post_retrieval:
    action: "rerank"
    rerank_type: "time_weighted"  # semantic | ppr | weighted

    # time_weighted 参数
    time_decay_rate: 0.1
    enable_reinforcement: true

    # ppr 参数
    # alpha: 0.15
    # max_iterations: 100

    # weighted 参数
    # semantic_weight: 0.5
    # time_weight: 0.3
    # topic_weight: 0.2
```

#### Filter 配置

```yaml
operators:
  post_retrieval:
    action: "filter"
    filter_type: "token_budget"  # top_k | threshold

    # token_budget 参数
    max_tokens: 2000

    # top_k 参数
    # k: 5

    # threshold 参数
    # threshold: 0.5
```

#### Merge 配置

```yaml
operators:
  post_retrieval:
    action: "merge"
    merge_type: "multi_tier"  # multi_query | link_expand | scm_three_way

    # multi_tier 参数
    tier_retrieval_limits:
      stm: 5
      mtm: 10
      ltm: 15
    rrf_k: 60

    # multi_query 参数
    # merge_strategy: "union"  # intersection

    # link_expand 参数
    # max_neighbors: 3
```

#### Augment 配置

```yaml
operators:
  post_retrieval:
    action: "augment"

    # augment 参数
    add_persona: true
    add_summary: true

    # augment.reinforce 参数 (在 rerank 中启用)
    # enable_reinforcement: true
```

### 4.2 推荐配置

#### 场景1: 长对话压缩

```yaml
# SCM风格
operators:
  post_retrieval:
    action: "filter"
    filter_type: "token_budget"
    max_tokens: 2000
```

#### 场景2: 多层记忆融合

```yaml
# MemGPT风格
operators:
  post_retrieval:
    action: "merge"
    merge_type: "multi_tier"
    tier_retrieval_limits:
      core: 5
      archival: 10
      recall: 15
    rrf_k: 60
```

#### 场景3: 时间敏感记忆

```yaml
# MemoryBank风格
operators:
  post_retrieval:
    action: "rerank"
    rerank_type: "time_weighted"
    time_decay_rate: 0.1
    enable_reinforcement: true
```

#### 场景4: 图知识推理

```yaml
# HippoRAG风格
operators:
  post_retrieval:
    action: "rerank"
    rerank_type: "ppr"
    alpha: 0.15
    max_iterations: 100
```

---

## 五、论文映射

### 5.1 12篇论文覆盖情况

| # | 论文 | 对应算子 | 覆盖状态 |
|---|------|---------|---------|
| 1 | TiM | `rerank.semantic` (通用) | ?? 部分 |
| 2 | MemoryBank | `rerank.time_weighted`, `augment.reinforce` | ? 完全 |
| 3 | MemGPT | `merge.multi_tier` | ? 完全 |
| 4 | A-Mem | `merge.link_expand` | ? 完全 |
| 5 | HippoRAG | `rerank.ppr` | ? 完全 |
| 6 | HippoRAG2 | `rerank.ppr` | ? 完全 |
| 7 | MemoryOS | `merge.multi_query`, `augment` | ? 完全 |
| 8 | LD-Agent | `rerank.weighted` | ? 完全 |
| 9 | SCM | `filter.token_budget`, `scm_three_way` | ? 完全 |
| 10 | Mem0 | `filter.threshold` | ? 完全 |
| 11 | Mem0? | `rerank.ppr` (可复用) | ?? 部分 |
| 12 | SeCom | (缺失) | ? 未覆盖 |

**覆盖率**: 9/12 完全覆盖 (75%)

### 5.2 数据结构适配矩阵

| 数据结构 | Rerank | Filter | Merge | Augment |
|---------|--------|--------|-------|---------|
| **分层式** (4篇) | `time_weighted` | `token_budget` | `multi_tier` | `augment` |
| **图结构** (3篇) | `ppr` | `threshold` | `link_expand` | `reinforce` |
| **分区式** (3篇) | `semantic` | `token_budget` | `scm_three_way` | `reinforce` |
| **混合式** (2篇) | `weighted` | `threshold` | `multi_query` | `augment` |

---

## 六、扩展开发

### 6.1 添加新算子

#### 步骤1: 创建算子文件

```python
# benchmarks/experiment/libs/post_retrieval/rerank/my_rerank.py
from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput

class MyRerankAction(BasePostRetrievalAction):
    """自定义重排序算子"""

    def _init_action(self) -> None:
        """初始化配置"""
        self.param1 = self.config.get("param1", default_value)

    def execute(self, input_data: PostRetrievalInput, service, llm=None) -> PostRetrievalOutput:
        """执行重排序"""
        # 1. 获取记忆数据
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        # 2. 执行重排序逻辑
        reranked_items = sorted(items, key=lambda x: self.compute_score(x))

        # 3. 返回结果
        return PostRetrievalOutput(
            memory_items=reranked_items,
            metadata={"action": "rerank.my_rerank"}
        )
```

#### 步骤2: 注册算子

```python
# benchmarks/experiment/libs/post_retrieval/registry.py
from .rerank.my_rerank import MyRerankAction

PostRetrievalActionRegistry.register("rerank.my_rerank", MyRerankAction)
```

#### 步骤3: 更新__init__.py

```python
# benchmarks/experiment/libs/post_retrieval/rerank/__init__.py
from .my_rerank import MyRerankAction

__all__ = [..., "MyRerankAction"]
```

### 6.2 算子开发规范

#### 必须实现的方法

```python
class MyAction(BasePostRetrievalAction):
    def _init_action(self) -> None:
        """初始化算子特定配置"""
        pass

    def execute(self, input_data, service, llm=None) -> PostRetrievalOutput:
        """执行算子逻辑"""
        pass
```

#### 数据结构约定

```python
# 输入
PostRetrievalInput(
    data={
        "memory_data": [{"text": str, "score": float, "metadata": dict}],
        "question": str
    },
    config=dict,
    service_name=str
)

# 输出
PostRetrievalOutput(
    memory_items=[MemoryItem(text, score, metadata, original_index)],
    metadata={"action": str, ...}
)
```

#### 调用记忆服务

```python
def execute(self, input_data, service, llm=None):
    # 多次检索（仅Merge类算子需要）
    additional_results = service.search(query="...", top_k=10)

    # 更新记忆（仅Augment类算子需要）
    service.update_memory_strength(memory_id, new_strength)
```

### 6.3 测试模板

```python
# tests/experiment/libs/post_retrieval/test_my_action.py
import pytest
from benchmarks.experiment.libs.post_retrieval import PostRetrievalInput, PostRetrievalOutput
from benchmarks.experiment.libs.post_retrieval.rerank.my_rerank import MyRerankAction

def test_my_rerank_action():
    # 准备配置
    config = {"param1": value1}
    action = MyRerankAction(config)

    # 准备输入
    input_data = PostRetrievalInput(
        data={
            "memory_data": [
                {"text": "A", "score": 0.9, "metadata": {}},
                {"text": "B", "score": 0.7, "metadata": {}}
            ],
            "question": "test query"
        },
        config=config,
        service_name="test_service"
    )

    # 执行算子
    output = action.execute(input_data, service=None, llm=None)

    # 验证输出
    assert len(output.memory_items) == 2
    assert output.memory_items[0].text == "A"
    assert output.metadata["action"] == "rerank.my_rerank"
```

---

## 七、FAQ

### Q1: 为什么不能同时使用多个算子？

**A**: 当前实现是单选模式，只能选择一种操作类型。未来计划支持Pipeline串联。

### Q2: 如何选择合适的算子？

**A**: 根据数据结构和需求选择：
- 分层结构 → `time_weighted` + `multi_tier`
- 图结构 → `ppr` + `link_expand`
- 长文本压缩 → `token_budget`

### Q3: 算子对性能有什么影响？

**A**:
- **Filter**: 几乎无开销
- **Rerank**: 取决于排序算法复杂度
- **Merge**: 需要多次检索，开销较大
- **Augment**: 可能需要额外LLM调用

### Q4: 如何添加自定义参数？

**A**: 在配置中添加，算子中通过 `self.config.get()` 读取。

---

## 八、参考文档

- [PAPER_MAPPING.md](./PAPER_MAPPING.md) - 论文映射详细分析
- [CLASSIFICATION_SUMMARY.md](./CLASSIFICATION_SUMMARY.md) - 分类体系总结
- [CLASSIFICATION_PRINCIPLES.md](./CLASSIFICATION_PRINCIPLES.md) - 分类原理可视化
- [base.py](./base.py) - 基类和数据模型
- [registry.py](./registry.py) - 注册表实现

---

## 九、更新日志

### v1.0 (2026-01-13)
- ? 实现13个算子 (4 Rerank + 3 Filter + 4 Merge + 2 Augment)
- ? 覆盖9/12篇论文
- ? 支持4种数据结构 (分层/图/分区/混合)
- ? 完整文档和测试

### 待办事项
- [ ] 实现 `filter.lsh_bucket` (TiM)
- [ ] 实现 `filter.semantic_cluster` (SeCom)
- [ ] 支持Pipeline串联
- [ ] 添加自适应算子选择
