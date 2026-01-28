# Memory Benchmark - 评估模块

## 📋 概述

本目录用于 Memory Benchmark 的实验结果分析与评估，特别是**ICML论文投稿的图表生成和美化**。

## 🎯 ICML 投稿专用指南 (NEW!)

为ICML论文准备图表？直接查看以下文档：

### 📚 核心文档

1. **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** ⭐⭐⭐
   - **最重要的文档！** 直接告诉您论文主体应该包含哪6张图
   - 图表-发现对应表
   - 质量检查清单

2. **[QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)** ⭐⭐
   - 三步走执行指南（10分钟快速美化）
   - 实用工具脚本
   - 常见问题解决

3. **[PAPER_FIGURE_SELECTION.md](PAPER_FIGURE_SELECTION.md)** ⭐
   - 详细的图表选择分析（216张图→6张核心图）
   - 美化技术细节
   - 配色方案和字体配置

### 🆕 增强功能 (2026-01-28)

**分析报告现在包含 Pre/Post Insert/Retrieval 详细时间分析！**

生成的 `analysis_report.md` 现在自动包含：

1. **Insert Time Breakdown (ms)** - 插入时间三阶段分解
   - **Pre-Insert Stage** (ms): 数据预处理、embedding生成、整合操作
   - **Memory-Insert Stage** (ms): 核心内存插入（向量索引、存储写入）
   - **Post-Insert Stage** (ms): 后处理、二级索引更新、清理

2. **Retrieval Time Breakdown (ms)** - 检索时间三阶段分解
   - **Pre-Retrieval Stage** (ms): 查询预处理、embedding生成、查询扩展
   - **Memory-Retrieval Stage** (ms): 核心检索操作（向量搜索、排序）
   - **Post-Retrieval Stage** (ms): 结果后处理、重排序、格式化

3. **Performance Insights** - 性能洞察
   - 自动识别最优策略（最高F1、最快Insert、最快Retrieval）
   - 阶段性能排名（Pre/Post阶段最慢策略Top 3）
   - 具体毫秒时间值，便于识别性能瓶颈

**示例报告片段**:
```markdown
## Insert Time Breakdown (ms)

**Pre-Insert Stage**: Data preprocessing, embedding generation, and consolidation operations.

| Strategy | Pre (ms) | Memory (ms) | Post (ms) | Total (ms) |
|----------|----------|-------------|-----------|------------|
| PostInsert_Mem0g_llm_crud | 1292.63 | 55.44 | 2502.18 | 3850.25 |
| PostInsert_Mem0g_none | 1837.23 | 85.28 | 0.04 | 1922.55 |

## Performance Insights

**Post-Insert Stage Impact**: Strategies with longest post-processing times:
1. PostInsert_Mem0g_llm_crud: 2502.18 ms  ← 明显的性能瓶颈！
2. PostInsert_Mem0g_link_evolution: 174.95 ms
```

**关键洞察**:
- llm_crud策略的Post-Insert阶段占用65%的总时间（2502ms），是主要瓶颈
- none策略几乎无Post-Insert开销（0.04ms），插入最快
- 所有策略的Pre-Retrieval阶段占50%以上时间，主要用于embedding生成

### 🚀 快速开始 (5分钟决策)

```bash
# 1. 查看执行摘要 - 了解推荐的6张核心图表
cat EXECUTIVE_SUMMARY.md

# 2. 应用美化补丁 (已提供现成配置)
# 编辑 benchmarks/evaluation/analysis/utils/plotting.py
# 添加 plotting_enhancements.py 中的配置

# 3. 重新生成美化版图表
bash benchmarks/evaluation/scripts/datastructure_locomo_evaluate.sh

# 4. 复制核心图表到论文目录
mkdir -p .sage/benchmark_paper/Figures/Experiment/
cp .sage/benchmarks/benchmark_memory/locomo/output/round_analysis_datastructure/comparison_*.pdf \
   .sage/benchmark_paper/Figures/Experiment/
```

### 🎨 美化工具

- **`analysis/utils/plotting_enhancements.py`**: 学术级美化补丁
  - 色盲友好调色板
  - Times字体配置
  - PDF双输出支持

- **`scripts/generate_paper_figures.py`**: 论文专用图表生成器
  - 定制化组合图
  - Pareto前沿散点图
  - 高级标注功能

---

## 📁 目录结构

```
evaluation/
├── README.md                          # 本文档
├── EXECUTIVE_SUMMARY.md              # 🎯 论文图表决策摘要 (从这里开始!)
├── QUICK_START_GUIDE.md              # 🚀 三步走执行指南
├── PAPER_FIGURE_SELECTION.md         # 📊 详细选择与美化建议
│
├── analysis/                          # 分析工具
│   ├── round_analyzer.py              # 轮次级分析引擎
│   └── utils/
│       ├── plotting.py                # 原始绘图工具
│       ├── plotting_enhancements.py   # 🎨 学术级美化补丁
│       ├── indicators.py              # 指标计算
│       └── data_loader.py             # 数据加载
│
└── scripts/                           # 评估脚本
    ├── datastructure_locomo_evaluate.sh
    ├── datastructure_longmemeval_evaluate.sh
    ├── datastructure_conflict_resolution_evaluate.sh
    └── generate_paper_figures.py      # 🎨 论文专用图表生成器
```

---

## 📊 实验结果概览

### 已完成的实验数据

#### 1. **LoCoMo** (主要实验平台)
- 📁 位置: `.sage/benchmarks/benchmark_memory/locomo/output/`
- 🎯 实验维度:
  - **DataStructure** (D1): 9种内存数据结构对比
  - **PreInsert** (D2): 写入路径标准化策略
  - **PreRetrieval** (D4): 查询构建策略
  - **PostInsert** (D3): 整合策略
  - **PostRetrieval** (D5): 后检索处理机制
- 📈 生成图表: ~150 PNG/PDF文件

#### 2. **LongMemEval** (验证集)
- 📁 位置: `.sage/benchmarks/benchmark_memory/longmemeval/output/`
- 🎯 实验维度: DataStructure only
- 📈 生成图表: ~30 PNG/PDF文件

#### 3. **MemAgentBench - Conflict Resolution** (验证集)
- 📁 位置: `.sage/benchmarks/benchmark_memory/conflict_resolution/output/`
- 🎯 实验维度: DataStructure only
- 📈 生成图表: ~30 PNG/PDF文件

### 论文关键发现 (K1-K5)

您的论文基于这些实验提出了5个关键发现：

- **K1**: 准确性提升会在读/写路径间转移成本 (cost budgeting)
- **K2**: 保留语义内容至关重要，过度压缩/关键词化有害
- **K3**: 数据结构决定准确性上限 (混合词法-语义检索最优)
- **K4**: 后检索复杂化(multi-query)成本高且效益低
- **K5**: 性能随内存增长衰减，时间相关问题最难

---

## 🎯 论文主体推荐图表

基于5个关键发现，**推荐在主体包含以下6张图表**：

| # | 图表 | 数据源 | 支撑发现 | 优先级 |
|---|------|--------|---------|--------|
| **Fig 2** | DataStructure F1对比 | LoCoMo DataStructure | K3, K5 | ⭐⭐⭐ |
| **Fig 3** | Category F1分解 | LoCoMo DataStructure | K5 | ⭐⭐⭐ |
| **Fig 4** | Insert vs Retrieval延迟 | LoCoMo DataStructure | K1 | ⭐⭐⭐ |
| **Fig 5** | 延迟分解 (堆叠图) | LoCoMo DataStructure | K1, K4 | ⭐⭐ |
| **Fig 6** | Normalization影响 | LoCoMo PreInsert | K2 | ⭐⭐ |
| **Fig 7** | Query Formulation影响 | LoCoMo PreRetrieval | K2 | ⭐ |

详见 [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)

---

## 🎨 图表美化状态

### ✅ 已提供的美化工具

1. **学术级配置** (`plotting_enhancements.py`)
   - ✅ 色盲友好调色板 (Wong 2011标准)
   - ✅ Times/Times New Roman字体
   - ✅ PDF + PNG双输出
   - ✅ 统一视觉风格

2. **论文专用生成器** (`generate_paper_figures.py`)
   - ✅ 组合图 (2x1子图)
   - ✅ Pareto前沿散点图
   - ✅ 高级标注和参考线
   - ⚠️ 需要连接实际数据 (当前使用模拟数据)

### 🔧 待执行的改进

- [ ] 将美化配置集成到 `plotting.py`
- [ ] 为所有绘图函数添加PDF输出
- [ ] 生成论文所需的6张核心图
- [ ] 验证PDF质量 (字体嵌入、DPI)

---

## 🚀 使用指南

### 场景1: 快速决策论文图表 (5分钟)

```bash
# 查看推荐的6张核心图表
cat EXECUTIVE_SUMMARY.md | grep "^### [0-9]"
```

### 场景2: 美化现有图表 (30分钟)

```bash
# 1. 查看快速指南
cat QUICK_START_GUIDE.md

# 2. 应用美化配置 (手动编辑 plotting.py)
# 参考 plotting_enhancements.py 的配置

# 3. 重新生成图表
bash scripts/datastructure_locomo_evaluate.sh
bash scripts/datastructure_longmemeval_evaluate.sh
bash scripts/datastructure_conflict_resolution_evaluate.sh
```

### 场景3: 生成论文专用图表 (1-2小时)

```bash
# 使用专用生成器
cd scripts/
python generate_paper_figures.py \
    --data-dir ../../../.sage/benchmarks/benchmark_memory/locomo/output/round_analysis_datastructure \
    --output ../../../.sage/benchmark_paper/Figures/Experiment/ \
    --figures all

# 注意: 需要先修改数据加载函数以连接实际CSV文件
```

---

## 📖 文档导航

### 🎯 决策类文档 (开始这里)
- **EXECUTIVE_SUMMARY.md**: 论文图表决策总结 (6张核心图)
- **QUICK_START_GUIDE.md**: 三步走执行指南

### 📚 参考类文档 (深入了解)
- **PAPER_FIGURE_SELECTION.md**: 详细的图表分析与美化建议

### 🔧 技术类文档
- **analysis/utils/plotting_enhancements.py**: 美化补丁代码
- **scripts/generate_paper_figures.py**: 论文图表生成器

---

## 🔍 常见问题

### Q1: 我应该从哪个文档开始？
**A**: 从 `EXECUTIVE_SUMMARY.md` 开始，它直接告诉您推荐哪6张图放在主体。

### Q2: 如何快速美化现有图表？
**A**: 查看 `QUICK_START_GUIDE.md` 的"第一步"部分，10分钟即可完成基础美化。

### Q3: 图表的颜色不够专业？
**A**: 使用 `plotting_enhancements.py` 中的色盲友好调色板，替换 `plotting.py` 的默认配色。

### Q4: 需要生成PDF格式吗？
**A**: 是的，ICML要求矢量格式。在 `plotting.py` 的所有 `savefig()` 调用处添加PDF输出。

### Q5: 如何确保所有图表风格一致？
**A**: 使用 `get_strategy_color()` 函数为每个策略分配固定颜色，确保相同策略在不同图中颜色一致。

---

## 📞 技术支持

### 美化相关问题
- 字体渲染问题 → 安装 `msttcorefonts` 或使用 `DejaVu Serif`
- PDF质量问题 → 确保 `matplotlib` backend设置为PDF
- 颜色不一致 → 使用 `SYSTEM_COLORS` 字典手动映射

### 数据加载问题
- CSV格式不匹配 → 检查 `analysis/utils/data_loader.py`
- 指标计算错误 → 验证 `analysis/utils/indicators.py`

---

## ✅ 提交前检查清单

在论文最终提交前，确保：

### 技术要求
- [ ] 所有图表 ≥ 300 DPI
- [ ] 格式为PDF (矢量)
- [ ] 字体为Times/Times New Roman
- [ ] 字号: 轴标签≥11pt, 刻度≥10pt

### 内容要求
- [ ] 每个关键发现有对应可视化
- [ ] 图表标题自解释
- [ ] 图例不遮挡数据
- [ ] 颜色编码一致

### 格式要求
- [ ] 符合ICML双栏格式
- [ ] 图表尺寸适配 (单列3.3英寸，双列7英寸)
- [ ] LaTeX引用正确

---

## 🎉 祝您投稿成功！

如有问题，请查阅相关文档或联系团队成员。

---

## 附录: 历史信息

### ⚠️ 早期状态说明

本模块最初处于探索阶段，采用专项分析方式。随着实验完成和论文撰写需求，现已升级为**论文图表生成与美化工具**。

## 🚀 快速开始

### 0. DataStructure-only datasets (MemAgentBench / LongMemEval)

本仓库当前已支持两套仅包含 **Memory Data Structure** 实验的工作负载：

- **MemAgentBench / Conflict Resolution**: `.sage/benchmarks/benchmark_memory/conflict_resolution/`
- **LongMemEval**: `.sage/benchmarks/benchmark_memory/longmemeval/`

对应的一键评估入口脚本在 `benchmarks/evaluation/scripts/`：

- `datastructure_conflict_resolution_evaluate.sh`
- `datastructure_longmemeval_evaluate.sh`

运行后会在各自的 `output/round_analysis_datastructure/` 目录下生成：
`analysis_report.md`、`comparison_*.png`、`*.csv` 等论文级图表与表格。

### 1. 指标探索

计算基础指标（F1、精确匹配率等）：

```bash
cd packages/sage-benchmark/src/sage/benchmark/benchmark_memory/evaluation/specialized_analysis

# 分析整个结果文件夹
python explore_metrics.py \
    --input /path/to/benchmark/results \
    --output ./results/metrics

# 只分析特定任务
python explore_metrics.py \
    --input /path/to/benchmark/results \
    --task conv-26 \
    --output ./results/metrics
```

### 2. 快速可视化

生成指标变化曲线和对比图：

```bash
# 从原始结果生成图表
python quick_visualize.py \
    --input /path/to/benchmark/results \
    --output ./results/plots

# 从已计算的指标文件生成图表
python quick_visualize.py \
    --input ./results/metrics/metrics_results.json \
    --mode from_metrics \
    --output ./results/plots
```

## 📊 当前支持的指标

### 准确性指标

- **Token-based F1**: 基于词级别的F1分数
- **Precision**: 精确率
- **Recall**: 召回率
- **Exact Match**: 精确匹配率（答案完全一致）

### 统计信息

- 各轮次指标值
- 平均值、最大值、最小值
- 跨任务对比

## 🔮 未来规划

等算法集成完成后，本模块将重构为**系统化评估框架**，包括：

### 1. 全面的评估指标

- **准确性**: F1、EM、ROUGE、BLEU等
- **效率**: 推理时间、内存使用、token消耗
- **鲁棒性**: 噪声干扰、长度变化的影响
- **可解释性**: 记忆召回分析、注意力可视化

### 2. 标准化报告

- 自动生成论文级别的对比图表
- LaTeX表格导出
- 统计显著性测试

### 3. 多维度对比

- 不同算法横向对比（LoCoMo vs LongMem vs ReMI）
- 不同数据集纵向分析（LongBench vs InfBench）
- 参数影响分析（记忆大小、更新策略等）

### 4. 消融实验支持

- 组件效果分析
- 超参数敏感性测试
- 最优配置推荐

## 📝 注意事项

1. **当前脚本仅供探索使用**，代码质量以快速迭代为主
1. **分析结果仅供参考**，不作为最终论文数据
1. **发现问题请及时记录**，为后续重构提供依据
1. 详细使用说明见 `specialized_analysis/README.md`

## 🤝 贡献指南

如果你在探索过程中：

- 发现有用的指标 → 记录在 `specialized_analysis/` 中
- 遇到数据格式问题 → 提issue或直接修复
- 有可视化想法 → 直接在脚本中尝试

所有探索性的工作都欢迎！等算法齐全后，我们会一起重构为正式的评估框架。
