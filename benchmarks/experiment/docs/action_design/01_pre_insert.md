# Pre-Insert Actions 设计维度

## 维度总览（3个维度）

| 维度 | 职责 | Action数量 |
|------|------|-----------|
| **None (透传)** | 无操作，直接传递原始数据 | 1 |
| Extract | 从原始数据提取结构化信息 | 4 |
| Transform | 转换数据格式以适配存储 | 2 |

> **💡 透传操作**: `none_action.py` 用于不需要预处理的系统（如 HippoRAG2, SCM），直接传递原始数据。

---

## 1. Extract 维度

**目的**: 将非结构化文本转换为可索引的结构化数据

| Action | 功能 | 输出格式 | 应用系统 |
|--------|------|---------|---------|
| **entity.py** | 实体提取 | 实体列表 [人名/地名/组织...] | 知识图谱、实体索引 |
| **fact.py** | 事实提取 | 事实陈述列表 | 事实验证、知识库 |
| **keyword.py** | 关键词提取 | 关键词列表 + 权重 | BM25检索、标签系统 |
| **triple.py** | 三元组提取 | SPO三元组 [(主语,谓语,宾语)...] | 知识图谱、关系推理 |

**技术特点**:
- 可组合：一次插入可同时提取多种信息
- 增量式：不破坏原始数据，只添加元数据
- 粒度范围：从细粒度（实体）到粗粒度（摘要）

---

## 2. Transform 维度

**目的**: 转换数据格式以适配不同存储后端

| Action | 转换类型 | 参数 | 应用场景 |
|--------|---------|------|---------|
| **segment_denoise.py** | 片段化 + 降噪 | segment_size, overlap, denoise_threshold | 长文本插入、噪声/格式混杂内容 |
| **summarize.py** | 摘要压缩 | method, ratio | 容量受限、快速预览、低冗余存储 |

---

## 组合使用示例

### 场景1: 长文档RAG（HippoRAG）
```yaml
pre_insert:
  - extract.triple           # 构建知识图谱
```

### 场景2: 对话记忆（MemoryOS）
```yaml
pre_insert:
  - extract.entity           # 提取对话实体
```

### 场景3: 知识库构建
```yaml
pre_insert:
  - extract.triple           # SPO三元组
  - extract.entity           # 实体识别
  - extract.keyword          # 关键词索引
```

---

## 与后续阶段的衔接

```
Pre-Insert输出 → 用于后续阶段

Extract结果:
  - triple → Post-Insert的graph_construction（构建图）
  - entity → Retrieval的实体匹配
  - summary → Retrieval的快速预览


```
