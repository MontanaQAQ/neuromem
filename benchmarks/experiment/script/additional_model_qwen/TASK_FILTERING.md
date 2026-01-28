# 任务过滤说明 (Task Filtering)

## 背景

由于硬件限制，Qwen-Plus实验的`Additional_Qwen_Mem0g_rewrite`策略仅运行了**8个任务**：
- `conv-26`, `conv-30`, `conv-41`, `conv-42`, `conv-43`, `conv-44`, `conv-47`, `conv-48`

而其他实验（PanGu基准和Qwen None）运行了**10个任务**（额外包含`conv-49`, `conv-50`）。

## 解决方案

为确保**公平对比**，我们在评估配置中添加了任务过滤机制：

### 配置文件

`benchmarks/evaluation/analysis/config/additional_model_qwen.yaml`:

```yaml
# 限制评估的任务列表（为公平对比，使用Qwen rewrite实际运行的8个任务）
# 注意: Qwen rewrite只跑了8个任务，其他实验跑了10个，统一使用这8个
tasks:
  - "conv-26"
  - "conv-30"
  - "conv-41"
  - "conv-42"
  - "conv-43"
  - "conv-44"
  - "conv-47"
  - "conv-48"
```

## 实际效果

| 实验 | 实际运行任务数 | 评估任务数 | 过滤情况 |
|------|---------------|-----------|---------|
| `PreInsert_Mem0g_none` | 10 | 8 | 过滤掉 conv-49, conv-50 |
| `PreInsert_Mem0g_rewrite_triplet_extract` | 10 | 8 | 过滤掉 conv-49, conv-50 |
| `Additional_Qwen_Mem0g_none` | 10 | 8 | 过滤掉 conv-49, conv-50 |
| `Additional_Qwen_Mem0g_rewrite` | 8 | 8 | 无需过滤 ✓ |

## 验证

运行以下命令验证任务过滤：

```bash
cd /home/zrc/develop_item/bench/neuromem

python -c "
import yaml
from pathlib import Path
from benchmarks.evaluation.analysis.utils.validators import discover_tasks

config_file = Path('benchmarks/evaluation/analysis/config/additional_model_qwen.yaml')
with open(config_file) as f:
    config = yaml.safe_load(f)

tasks_filter = config.get('tasks', [])
print(f'配置的任务过滤列表: {tasks_filter}')
print(f'任务数: {len(tasks_filter)}')
print()

base_dir = Path('.sage/benchmarks/benchmark_memory/locomo')
strategies = [
    'PreInsert_Mem0g_none',
    'PreInsert_Mem0g_rewrite_triplet_extract',
    'Additional_Qwen_Mem0g_none',
    'Additional_Qwen_Mem0g_rewrite'
]

for strategy in strategies:
    tasks = discover_tasks(base_dir / strategy)
    filtered = [t for t in tasks if t in tasks_filter]
    print(f'{strategy}:')
    print(f'  实际: {len(tasks)}个 | 过滤后: {len(filtered)}个')
"
```

预期输出：
```
配置的任务过滤列表: ['conv-26', 'conv-30', 'conv-41', 'conv-42', 'conv-43', 'conv-44', 'conv-47', 'conv-48']
任务数: 8

PreInsert_Mem0g_none:
  实际: 10个 | 过滤后: 8个
PreInsert_Mem0g_rewrite_triplet_extract:
  实际: 10个 | 过滤后: 8个
Additional_Qwen_Mem0g_none:
  实际: 10个 | 过滤后: 8个
Additional_Qwen_Mem0g_rewrite:
  实际: 8个 | 过滤后: 8个
```

## 代码实现

### 1. 配置文件 (`additional_model_qwen.yaml`)

添加`tasks`字段指定允许的任务列表。

### 2. DataLoader增强 (`utils/data_loader.py`)

修改了以下方法支持`tasks_filter`参数：
- `DataLoader.iter_tasks(strategy, tasks_filter=None)`
- `DataLoader.get_tasks(strategy, tasks_filter=None)`
- `RoundAnalyzer.aggregate_across_tasks(..., tasks_filter=None)`
- `CategoryAnalyzer.aggregate_across_tasks(..., tasks_filter=None)`
- `TimeBreakdownAnalyzer.aggregate_across_tasks(..., tasks_filter=None)`

### 3. 分析器传递 (`round_analyzer.py`)

```python
# 从配置读取任务过滤列表
tasks_filter = config.get("tasks", None)

# 传递给所有分析器
f1_metrics = analyzer.aggregate_across_tasks(loader, strategy, "f1", tasks_filter)
category_f1 = category_analyzer.aggregate_across_tasks(loader, strategy, tasks_filter)
insert_breakdown = time_analyzer.aggregate_across_tasks(loader, strategy, "insert", tasks_filter)
```

## 通用性

此机制不仅适用于Qwen实验，也可用于任何需要限制评估任务的场景：

### 示例1：评估特定类别

```yaml
# 仅评估Multi-answer问题
tasks:
  - "conv-26"  # Category 1
  - "conv-30"  # Category 1
```

### 示例2：对比子集

```yaml
# 对比前5个任务
tasks:
  - "conv-26"
  - "conv-30"
  - "conv-41"
  - "conv-42"
  - "conv-43"
```

## 最佳实践

1. **记录原因**: 在配置文件注释中说明为什么需要任务过滤
2. **验证结果**: 运行验证脚本确认过滤正确
3. **报告透明**: 在分析报告中明确说明使用了任务过滤
4. **保持一致**: 所有对比实验使用相同的任务列表

## 日志输出

运行分析时会显示任务过滤信息：

```
======================================================================
开始分析 (4 个策略)
======================================================================

任务过滤: 仅评估 8 个任务: ['conv-26', 'conv-30', 'conv-41', 'conv-42', 'conv-43', 'conv-44', 'conv-47', 'conv-48']

[PreInsert_Mem0g_none]
  F1 Scores: {1: 0.45, 2: 0.52, ...}
  ...
```

## 相关文件

- 配置: `benchmarks/evaluation/analysis/config/additional_model_qwen.yaml`
- 数据加载: `benchmarks/evaluation/analysis/utils/data_loader.py`
- 分析器: `benchmarks/evaluation/analysis/round_analyzer.py`
- 验证工具: `benchmarks/evaluation/analysis/utils/validators.py`
