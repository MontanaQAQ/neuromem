# Pre-Insert Actions 设计重构（none + enrich + rewrite）

## 维度总览（3类）

基于插入管线的统一输出形态（统一为 `text + metadata`），我们将 Pre-Insert 行为归纳为三类：

| 类别 | 职责 | 输出形态 | 典型基数 |
| :--- | :--- | :--- | :--- |
| **None（透传）** | 不做任何处理，直接传递原始对话。 | text（原文） + metadata（可为空） | 1→1 |
| **Enrich（增润）** | 可保持原文或产出变换文本，在 metadata 中附加信息。 | text（原文或变换后） + metadata（增强项） | 1→1 或 1→N |
| **Rewrite（重写）** | 对文本进行规整/摘要/净化。 | text（重写后，仅文本） | 1→1 或 1→N（按实现） |

> 设计要点：
> - 所有算子最终产出均必须包含非空 `text` 字段，`metadata` 为可选增强。
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
| `enrich/segment_compress.py`（概念：`enrich.segment_compress`） | 语义分段/压缩去噪并增润 | text（句段化或压缩后） + metadata（段位/统计/摘要等） | SeCom，长文档问答 |
| `enrich/entity.py` | 实体抽取并增润 | text（实体字符串） + metadata（类型/索引等） | Mem0，实体链接 |

**技术特点**：
- 1→1 或 1→N 映射（按实现）；`text` 可为原文或变换后的文本。
- 核心增益来自 metadata 中的结构化信息（关键词、标签、上下文）。
- 检索侧可选择：仅用 text，或将部分 metadata 拼接进 text 作为 BM25 覆盖。

---

## 3. Rewrite（重写型）

**目的**：对输入文本进行摘要、规整或净化，使其更适合向量与文本索引；在需要时也可生成多条更细粒度的文本。

| Action（命名） | 功能 | 输出示例 | 应用系统/场景 |
| :--- | :--- | :--- | :--- |
| `rewrite.fact_extract`（实现：`rewrite/fact_extract.py`） | 原子事实重写 | text（事实短句） | Mem0，事实库构建 |
| `rewrite.triplet_extract`（实现：`rewrite/triplet_extract.py`） | 三元组重写 | text（SPO重构语句） | TiM/HippoRAG，知识图谱构建 |

**技术特点**：
- 1→1 或 1→N（按实现）。
- 仅产出 `text`（不新增 metadata）；如需元数据，请使用 Enrich 或组合策略。
- 与 Enrich 的区别：Rewrite 直接作用于 `text` 内容本身（摘要/规整/句段化），不做元数据增强。

注：当前 `fact.py` 与 `triple.py` 的实现会写入部分 `metadata`（如索引/实体字段），若需严格符合“Rewrite 不含 metadata”，可通过新增配置开关（如 `write_metadata: false`）或在上游统一剥离元数据来对齐规范。

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
  - enrich.segment_compress   # 语义分段与压缩去噪（text+metadata，可多条）
```

### 场景3：对照与兼容
```yaml
pre_insert:
  - none                 # 作为基线
  - enrich.keyword       # 增加标签用于混合检索
  - rewrite.summarize    # 增加摘要用于快速预览与向量检索
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

## 命名与兼容（建议）

- 新命名空间：
  - `none.*`、`enrich.*`、`rewrite.*`
- 典型映射：
  - `transform.keyword` → `enrich.keyword`
  - `transform.summarize` → `enrich.summarize`
  - `transform.segment_denoise` / `transform.segment_compress` → `enrich.segment_compress`
  - `extract.entity` → `enrich.entity`
  - `extract.fact` / `extract.triple` → `rewrite.fact_extract` / `rewrite.triplet_extract`
- 说明：是否入索引与索引类型由集合配置决定（与分类正交）。

---

## 完整算子清单与分类（当前实现）

- None（透传）
  - `none_action.py`: 直接透传原文。
- Enrich（增润）
  - `enrichment/keyword.py`: 关键词/标签/上下文 Note 增润（1→1）。
  - `enrichment/summarize.py`（概念 `enrich.summarize`）：摘要/规整并增润（1→1 或 1→N）。
  - `enrich/segment_compress.py`（概念 `enrich.segment_compress`）：语义分段/压缩去噪并增润（多条）。
  - `decomposition/entity.py`: 抽取实体为多条，并附类型等 metadata（1→N）。
- Rewrite（重写，仅文本）
  - `rewrite/fact_extract.py`（对应 `rewrite.fact_extract` 概念）：重写为事实短句（当前实现含 metadata，推荐加开关关闭）。
  - `rewrite/triplet_extract.py`（对应 `rewrite.triplet_extract` 概念）：重写为 SPO 语句（当前实现含 metadata，推荐加开关关闭）。
