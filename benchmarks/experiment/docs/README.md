# NeuroMem Benchmark 实验文档

> **更新**: 2026-01-13  
> **版本**: v2.0 - 精简版

---

## 📚 文档结构

```
docs/
├── README.md                    # 本文件 - 文档导航
├── EXPERIMENT_GUIDE.md          # ⭐ 核心指南 - 五维实验框架与快速开始
└── action_design/               # Action层详细设计
    ├── 00_overview.md           # 四阶段Action总览
    ├── 01_pre_insert.md         # PreInsert Actions详细设计
    ├── 02_pre_retrieval.md      # PreRetrieval Actions详细设计
    ├── 03_post_insert.md        # PostInsert Actions详细设计
    └── 04_post_retrieval.md     # PostRetrieval Actions详细设计
```

---

## 🚀 快速开始

### 新用户入门

**推荐阅读顺序**：
1. [EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md) - 了解核心架构和五维框架
2. [action_design/00_overview.md](action_design/00_overview.md) - 了解Action层设计
3. 根据需要查看具体Action详细文档

### 实验配置

**配置文件路径**: `benchmarks/experiment/config/`

```bash
# 查看所有可用配置
ls benchmarks/experiment/config/primitive_memory_model/
ls benchmarks/experiment/config/query_formulation_strategy/
```

**运行实验**:
```bash
# 方式1: 直接运行配置文件
python benchmarks/experiment/memory_test_pipeline.py \
  --config config/primitive_memory_model/locomo_tim_pipeline.yaml \
  --task_id conv-26

# 方式2: 使用预定义脚本
bash benchmarks/experiment/script/query_formulation_strategy/run_tim_locomo_embedding.sh
```

---

## 📖 文档说明

### EXPERIMENT_GUIDE.md - 核心实验指南

**内容**：
- ✅ 五维实验框架（D1-D5）
- ✅ 数据结构分类（Partitional vs Hierarchical）
- ✅ 论文算法映射
- ✅ 分阶段实验设计
- ✅ 配置文件模板
- ✅ 快速开始指南

**适用场景**：
- 设计新实验
- 理解系统架构
- 配置实验参数

### action_design/ - Action层设计

**内容**：
- 四个阶段的Action详细设计
- 每个Action的参数说明
- 配置示例
- 论文映射关系

**适用场景**：
- 实现新的Action
- 理解现有Action的工作原理
- 调试Action配置

---

## 🗂️ 相关资源

### 配置目录

| 目录 | 说明 | 数量 |
|------|------|------|
| `config/primitive_memory_model/` | 论文原始配置 | 13个 |
| `config/query_formulation_strategy/` | D4实验（PreRetrieval） | 12个 |
| `config/result_optimization_strategy/` | D5实验（PostRetrieval） | - |
| `config/normalization_strategy/` | D2实验（PreInsert） | - |
| `config/consolidation_policy/` | D3实验（PostInsert） | - |
| `config/memory_data_structure/` | D1实验（MemoryService） | - |

### 代码实现

| 模块 | 路径 |
|------|------|
| MemoryService | `sage/neuromem/services/` |
| Pipeline Operators | `benchmarks/experiment/libs/` |
| Action Registry | `benchmarks/experiment/libs/*/registry.py` |

### 脚本工具

| 工具 | 路径 |
|------|------|
| 实验执行脚本 | `benchmarks/experiment/script/` |
| 结果分析工具 | `benchmarks/experiment/tools/` |

---

## 📝 版本历史

**v2.0 (2026-01-13)**:
- ✅ 整合7个分散文档为单一核心指南
- ✅ 移除过时的reference代码引用
- ✅ 精简为2个核心文档 + action设计子目录
- ✅ 基于当前代码实现更新所有内容

**v1.x (历史)**:
- 包含多个分散文档（已归档）
- 包含reference代码示例（已移除）

---

## 🔗 相关文档

**项目级文档**: `/home/zrc/develop_item/bench/neuromem/docs/`
- 项目整体架构
- PyPI发布指南
- CI/CD配置

**Benchmark文档**: `/home/zrc/develop_item/bench/neuromem/benchmarks/ARCHITECTURE.md`
- Benchmark系统架构
- 评估指标说明

---

## 💡 贡献指南

如需更新文档：
1. **EXPERIMENT_GUIDE.md**: 实验框架、配置模板、快速开始
2. **action_design/**: Action层技术细节
3. 保持文档与代码实现同步
4. 移除过时信息和reference引用

**联系**: 查看项目 `/home/zrc/develop_item/bench/neuromem/CONTRIBUTING.md`
