# Pre-Insert Actions 设计重构（none + enrich + rewrite）

## 维度总览（3类）

基于插入管线的统一输出形态（统一为 `text + metadata`），我们将 Pre-Insert 行为归纳为三类：

| 类别 | 职责 | 输出形态 | 典型基数 |
| :--- | :--- | :--- | :--- |
| **None（透传）** | 不做任何处理，直接传递原始对话。 | text（原文） + metadata（可为空） | 1→1 |
| **Enrich（增润）** | 可保持原文或产出变换文本，在 metadata 中附加信息。 | text（原文或变换后） + metadata（增强项） | 1→1 或 1→N |
| **Rewrite（重写）** | 对文本进行规整/摘要/净化。 | text（重写后）| 1→1 或 1→N（按实现） |

> 设计要点：
> - “是否入索引”取决于集合配置（BM25/FAISS/LSH/Segment 等），与分类正交。

---

## 1. None（透传）

**目的**：保持最小改动，原样进入插入阶段，作为基线或与其他算子组合的对照组。

- 输出格式：
  - `text`: 原始对话（串联后的文本）
  - `metadata`: `{}` 或携带来源/时间等基础字段
- 适用场景：
  - 作为对照实验的基线；与 Enrich/Rewrite 组合时保留原文

---

## 2. Enrich（增润型）

**目的**：在可保持原文或对 `text` 进行轻量变换的前提下，附加结构化元数据，提升可检索性与可理解性。

| Action | 功能 | 输出示例 | 应用系统/场景 |
| :--- | :--- | :--- | :--- |
| `enrich/keyword.py` | Note/标签提取 | text（原文或变换后） + metadata.note = {keywords, context, tags} | A-Mem，标签分类/混合检索 |
| `enrich/summarize.py`（概念：`enrich.summarize`） | 摘要生成/规整并增润 | text（摘要或规整） + metadata（长度/阈值/LLM信息等） | MemGPT、SCM、长对话回顾 |
| `enrich/entity.py` | 实体抽取并增润 | text（实体字符串） + metadata（类型/索引等） | Mem0，实体链接 |

**技术特点**：
- 1→1 或 1→N 映射（按实现）；`text` 可为原文或变换后的文本。
- 核心增益来自 metadata 中的结构化信息（关键词、标签、上下文）。
- 检索侧可选择：仅用 text，或将部分 metadata 拼接进 text 作为 BM25 覆盖。

---

## 3. Rewrite（重写型）

**目的**：对输入文本进行摘要、规整或净化，使其更适合向量与文本索引。

| Action（命名） | 功能 | 输出示例 | 应用系统/场景 |
| :--- | :--- | :--- | :--- |
| `rewrite.compress`（实现：`rewrite/compress.py`） | 语义分段/压缩去噪（SeCom） | text（句段化或压缩后） + metadata（按开关） | SeCom，长文档问答 |
| `rewrite.fact_extract`（实现：`rewrite/fact_extract.py`） | 原子事实重写 | text（事实短句） | Mem0，事实库构建 |
| `rewrite.triplet_extract`（实现：`rewrite/triplet_extract.py`） | 三元组重写 | text（SPO重构语句） | TiM/HippoRAG，知识图谱构建 |

**技术特点**：
- 1→1 或 1→N（按实现）。
- 以产出 `text` 为主；部分实现（如 `rewrite.compress`、当前的 fact/triple 实现）可按配置写入少量 metadata（可通过开关关闭）。
- 与 Enrich 的区别：Rewrite 直接作用于 `text` 内容本身（摘要/规整/句段化），不以新增结构化 metadata 为主要目标。

注：当前 `rewrite.compress`、`fact_extract` 与 `triplet_extract` 的实现可写入部分 `metadata`（如段位/统计/实体字段）。若需严格限制 Rewrite 的元数据输出，可通过配置开关（如 `write_metadata: false`）或在上游统一剥离元数据来对齐规范。

---

## 组合使用示例

### 场景1：保留原文并增润
```yaml
pre_insert:
  - none                 # 透传原文
  - enrich.keyword       # 在 metadata.note 中附加 {keywords, context, tags}
```

### 场景2：长对话摘要与段落化（增润）
```yaml
pre_insert:
  - enrich.summarize         # 生成摘要/规整后的文本（text+metadata）
  - rewrite.compress          # 语义分段与压缩去噪（text 为主，可选 metadata，可多条）
```

### 场景3：对照与兼容
```yaml
pre_insert:
  - none                 # 作为基线
  - enrich.keyword       # 增加标签用于混合检索
  - enrich.summarize     # 增加摘要用于快速预览与向量检索
```

---

## 与后续阶段的衔接

```
Pre-Insert 输出 → 插入（MemoryInsert）→ 统一集合（UnifiedCollection）

None：
  - text：原文；metadata：基础字段
  - 适合作为检索与评估的基线

Enrich：
  - text：保持原文；metadata：携带 note（keywords/context/tags）等结构化增强
  - 检索：BM25 可拼接 note；向量索引通常使用 text

Rewrite：
  - text：摘要/规整/句段化后的文本（可能多条）
  - 检索：更短更聚焦的文本，便于向量/文本索引；不新增 metadata
```

---

## 完整算子清单与分类（当前实现）

- None（透传）
  - `none_action.py`: 直接透传原文。
- Enrich（增润）
  - `enrich/keyword.py`: 关键词/标签/上下文 Note 增润（1→1）。
  - `enrich/summarize.py`（概念 `enrich.summarize`）：摘要/规整并增润（1→1 或 1→N）。
  - `enrich/entity.py`: 抽取实体为多条，并附类型等 metadata（1→N）。
- Rewrite（重写）
  - `rewrite/compress.py`（对应 `rewrite.compress` 概念）：语义分段/压缩去噪（SeCom，text 为主，metadata 可选）。
  - `rewrite/fact_extract.py`（对应 `rewrite.fact_extract` 概念）：重写为事实短句（可选 metadata）。
  - `rewrite/triplet_extract.py`（对应 `rewrite.triplet_extract` 概念）：重写为 SPO 语句（可选 metadata）。
