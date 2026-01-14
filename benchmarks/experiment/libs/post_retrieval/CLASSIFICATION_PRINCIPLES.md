# PostRetrieval 分类体系可视化

## 一、分类依据：操作类型维度

```
PostRetrieval 后处理算子分类
         |
         ├─── 操作目的 (What)
         ├─── 数据流向 (How)
         └─── 适配结构 (Where)
```

---

## 二、四类操作的分类逻辑

### ? Rerank (重排序)
**核心特征**: 不改变结果集大小，只调整顺序

```
输入: [A, B, C, D, E]
操作: 根据某种评分函数重新排序
输出: [C, A, E, B, D]  (数量不变)
```

**分类依据**:
- ? 保持结果数量
- ? 改变结果顺序
- ? 不添加/删除结果
- ? 不修改结果内容

**实现方式**:
- 时间权重: $score_{new} = score_{sim} \times e^{-\lambda t}$
- PPR图遍历: $score_{new} = \alpha \cdot PPR(node) + (1-\alpha) \cdot sim$
- 多因子加权: $score_{new} = w_1 \cdot sim + w_2 \cdot time + w_3 \cdot topic$

---

### ? Filter (过滤)
**核心特征**: 减少结果集大小，不改变顺序

```
输入: [A(0.9), B(0.7), C(0.5), D(0.3), E(0.1)]
操作: 过滤掉不满足条件的结果
输出: [A(0.9), B(0.7), C(0.5)]  (数量减少)
```

**分类依据**:
- ? 减少结果数量
- ? 保持原有顺序 (相对位置)
- ? 不改变排序
- ? 不修改结果内容

**实现方式**:
- Top-K: 保留前K个
- 阈值过滤: $score > threshold$
- Token预算: $\sum tokens \leq budget$

---

### ? Merge (合并)
**核心特征**: 整合多次检索，可能增加结果

```
输入1: [A, B, C]  (第一次检索)
输入2: [B, D, E]  (第二次检索)
操作: 合并去重、融合排序
输出: [A, B, C, D, E]  (数量可能增加)
```

**分类依据**:
- ? 整合多个来源
- ? 可能增加结果数量
- ? 需要重新排序/去重
- ? 不修改单个结果内容

**实现方式**:
- 多层融合: RRF(tier1, tier2, tier3)
- 链接扩展: 原始结果 + 邻居节点
- 多查询合并: Union / Intersection

---

### ? Augment (增强)
**核心特征**: 为结果添加额外信息，修改内容

```
输入: [{"text": "用户说了A", "score": 0.9}]
操作: 添加上下文、更新元数据
输出: [{"text": "用户说了A", "score": 0.9,
        "persona": "活泼", "context": "在讨论兴趣时",
        "access_count": 3}]  (内容增加)
```

**分类依据**:
- ? 修改结果内容
- ? 添加元数据/上下文
- ? 可能更新数据库
- ? 不改变结果数量
- ? 不改变结果顺序

**实现方式**:
- 上下文增强: 添加persona/traits/summary
- 记忆强化: 更新access_count/strength

---

## 三、四类操作的决策树

```
检索到N个结果后...
  |
  ├─ 需要调整顺序？
  |    └─ Yes → 【Rerank】
  |
  ├─ 需要减少数量？
  |    └─ Yes → 【Filter】
  |
  ├─ 需要整合多次检索？
  |    └─ Yes → 【Merge】
  |
  └─ 需要添加额外信息？
       └─ Yes → 【Augment】
```

---

## 四、与数据结构的适配关系

### 4.1 分层式结构 (Hierarchical)

```
STM (短期)
MTM (中期)  ← 多层检索
LTM (长期)
```

**最适配的操作**:
- ? **Merge**: 多层融合 (`multi_tier`, `multi_query`)
- ? **Rerank**: 时间加权 (`time_weighted`)
- ? **Augment**: 添加层级上下文 (`augment`)
- ?? **Filter**: 通用过滤 (`token_budget`)

**代表论文**: MemoryBank, MemGPT, MemoryOS, LD-Agent

---

### 4.2 图结构 (Graph)

```
实体节点 ─边关系→ 实体节点
    ↓                ↓
  属性            属性
```

**最适配的操作**:
- ? **Rerank**: PPR图遍历 (`ppr`)
- ? **Merge**: 链接扩展 (`link_expand`)
- ?? **Filter**: 阈值过滤 (`threshold`)
- ?? **Augment**: 记忆强化 (`reinforce`)

**代表论文**: A-Mem, HippoRAG, Mem0?

---

### 4.3 分区式结构 (Partitional)

```
桶1 [A, B, C]
桶2 [D, E, F]  ← 分桶存储
桶3 [G, H, I]
```

**最适配的操作**:
- ? **Filter**: Token预算 (`token_budget`)
- ? **Merge**: 三元决策 (`scm_three_way`)
- ? **Rerank**: 语义重排 (`semantic`)
- ?? **Augment**: 记忆强化 (`reinforce`)

**代表论文**: TiM, SCM, SeCom

---

### 4.4 混合式结构 (Hybrid)

```
Vector索引 + BM25索引 + (可选图索引)
```

**最适配的操作**:
- ? **Rerank**: 多因子加权 (`weighted`)
- ? **Filter**: 阈值过滤 (`threshold`)
- ?? **Merge**: 多查询合并 (`multi_query`)
- ?? **Augment**: 上下文增强 (`augment`)

**代表论文**: Mem0

---

## 五、Pipeline中的执行顺序

```
MemoryRetrieval (检索)
         ↓
PostRetrieval (后处理)
    |
    ├─ Step 1: Merge (如果有多次检索)
    |           ↓
    ├─ Step 2: Rerank (调整顺序)
    |           ↓
    ├─ Step 3: Filter (减少数量)
    |           ↓
    └─ Step 4: Augment (添加信息)
         ↓
MemoryEvaluation (评估)
```

**执行顺序逻辑**:
1. **Merge优先**: 先整合所有来源
2. **Rerank次之**: 在完整集合上排序
3. **Filter再次**: 在排序后筛选Top-K
4. **Augment最后**: 对最终结果增强

**注意**: 当前实现是**单选模式**，只能选择一种操作类型。

---

## 六、各类算子的通用性对比

| 类别 | 通用性 | 数据结构依赖 | 实现复杂度 |
|------|--------|-------------|-----------|
| **Filter** | ????? | 无特殊依赖 | 低 |
| **Rerank** | ???? | 需要score字段 | 中 |
| **Augment** | ??? | 需要额外数据源 | 中-高 |
| **Merge** | ?? | 依赖特定结构 | 高 |

**通用性排名**: Filter > Rerank > Augment > Merge

---

## 七、选择算子的决策指南

### 场景1: 长对话压缩
**问题**: 检索结果太多，超出LLM上下文窗口  
**推荐**: `filter.token_budget` (SCM)  
**理由**: 直接控制token数量，保证可用

### 场景2: 多层记忆融合
**问题**: 需要同时查询STM/MTM/LTM  
**推荐**: `merge.multi_tier` (MemGPT)  
**理由**: RRF算法成熟，适配分层结构

### 场景3: 时间敏感记忆
**问题**: 需要强调近期记忆  
**推荐**: `rerank.time_weighted` (MemoryBank)  
**理由**: 数学模型严谨，可调节衰减率

### 场景4: 图知识推理
**问题**: 需要多跳关系推理  
**推荐**: `rerank.ppr` + `merge.link_expand` (HippoRAG + A-Mem)  
**理由**: 图遍历获取关联知识

### 场景5: 上下文增强
**问题**: 需要添加用户画像、主题摘要  
**推荐**: `augment` (MemoryOS)  
**理由**: 完整的上下文信息提升LLM理解

---

## 八、总结

### 分类依据的本质

| 维度 | 分类标准 |
|------|---------|
| **数据流** | 输入→操作→输出的转换方式 |
| **结果集** | 数量变化(增/减/不变) |
| **内容** | 是否修改单个结果 |
| **来源** | 单次检索 vs 多次检索 |

### 核心设计原则

1. **单一职责**: 每类操作只负责一种转换
2. **可组合性**: 不同类可串联使用
3. **数据结构无关**: 尽量通用化
4. **论文驱动**: 每个算子对应论文实现

### 扩展方向

- [ ] 支持**Pipeline串联** (Merge→Rerank→Filter→Augment)
- [ ] 添加**自适应选择** (根据数据结构自动选择算子)
- [ ] 实现**参数优化** (AutoML调参)
