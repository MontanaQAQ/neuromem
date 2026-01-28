# Qwen评估脚本任务过滤修改总结

## 问题背景

用户反馈：
> "qwen这个评估脚本得改一下。迫于硬件设置，我们只跑了conv-26到48（.sage/benchmarks/benchmark_memory/locomo/Additional_Qwen_Mem0g_rewrite你去看一下，这里不是线性增加的）。为了公平期间，其余几个实验我希望也都是这几个文件参与评估"

**实际情况**:
- `Additional_Qwen_Mem0g_rewrite`: 仅跑了8个任务（conv-26, 30, 41-44, 47-48）
- 其他3个实验: 跑了10个任务（额外包含conv-49, conv-50）
- **问题**: 对比不公平，需要统一使用8个任务进行评估

## 解决方案

### 1. 配置文件添加任务过滤

**文件**: `benchmarks/evaluation/analysis/config/additional_model_qwen.yaml`

**修改**: 添加`tasks`字段

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

### 2. DataLoader增强

**文件**: `benchmarks/evaluation/analysis/utils/data_loader.py`

**修改内容**:

#### 2.1 `DataLoader.iter_tasks()` - 添加任务过滤参数

```python
def iter_tasks(self, strategy: str, tasks_filter: list[str] | None = None) -> Iterator[TaskData]:
    """
    迭代策略下的所有task

    Args:
        strategy: 策略目录名
        tasks_filter: 可选的任务过滤列表（如 ['conv-26', 'conv-30']）
                     如果提供，只加载这些任务；否则加载所有任务
    """
    strategy_dir = self.base_dir / strategy
    tasks = discover_tasks(strategy_dir)

    # 应用任务过滤
    if tasks_filter is not None:
        tasks = [t for t in tasks if t in tasks_filter]

    for task in tasks:
        task_data = self.load_task(strategy, task)
        if task_data is not None:
            yield task_data
```

#### 2.2 `DataLoader.get_tasks()` - 添加任务过滤参数

```python
def get_tasks(self, strategy: str, tasks_filter: list[str] | None = None) -> list[str]:
    """获取策略下的所有task名称

    Args:
        strategy: 策略目录名
        tasks_filter: 可选的任务过滤列表

    Returns:
        任务名称列表
    """
    tasks = discover_tasks(self.base_dir / strategy)
    if tasks_filter is not None:
        tasks = [t for t in tasks if t in tasks_filter]
    return tasks
```

#### 2.3 `RoundAnalyzer.aggregate_across_tasks()` - 传递过滤参数

```python
def aggregate_across_tasks(
    self,
    loader: DataLoader,
    strategy: str,
    metric_func: str = "f1",
    tasks_filter: list[str] | None = None,  # 新增参数
) -> dict[int, float]:
    # ...
    for task_data in loader.iter_tasks(strategy, tasks_filter):  # 传递过滤器
        # ...
```

#### 2.4 `CategoryAnalyzer.aggregate_across_tasks()` - 传递过滤参数

```python
def aggregate_across_tasks(
    self,
    loader: DataLoader,
    strategy: str,
    tasks_filter: list[str] | None = None,  # 新增参数
) -> dict[int, float]:
    # ...
    for task_data in loader.iter_tasks(strategy, tasks_filter):  # 传递过滤器
        # ...
```

#### 2.5 `TimeBreakdownAnalyzer.aggregate_across_tasks()` - 传递过滤参数

```python
def aggregate_across_tasks(
    self,
    loader: DataLoader,
    strategy: str,
    timing_type: str = "insert",
    tasks_filter: list[str] | None = None,  # 新增参数
) -> dict[str, float]:
    # ...
    for task_data in loader.iter_tasks(strategy, tasks_filter):  # 传递过滤器
        # ...
```

### 3. 分析器传递任务过滤

**文件**: `benchmarks/evaluation/analysis/round_analyzer.py`

**修改**: 从配置读取任务列表并传递给所有分析器

```python
# 获取任务过滤列表（如果配置中指定）
tasks_filter = config.get("tasks", None)
if tasks_filter:
    print(f"\n任务过滤: 仅评估 {len(tasks_filter)} 个任务: {tasks_filter}")
else:
    print("\n任务过滤: 未指定，评估所有任务")

# ...

# 聚合指标（传递任务过滤器）
f1_metrics = analyzer.aggregate_across_tasks(loader, strategy, "f1", tasks_filter)
insert_metrics = analyzer.aggregate_across_tasks(loader, strategy, "insert_time", tasks_filter)
retrieval_metrics = analyzer.aggregate_across_tasks(loader, strategy, "retrieval_time", tasks_filter)

# Category F1分析
category_f1 = category_analyzer.aggregate_across_tasks(loader, strategy, tasks_filter)

# 时间分解分析
insert_breakdown = time_analyzer.aggregate_across_tasks(loader, strategy, "insert", tasks_filter)
retrieval_breakdown = time_analyzer.aggregate_across_tasks(loader, strategy, "retrieval", tasks_filter)
```

### 4. 文档更新

**新增文件**:
- `benchmarks/experiment/script/additional_model_qwen/TASK_FILTERING.md`: 任务过滤详细说明

**更新文件**:
- `benchmarks/experiment/script/additional_model_qwen/analyze_qwen_comparison.sh`: 添加任务说明

## 验证结果

```bash
======================================================================
任务过滤功能验证
======================================================================

✓ 配置文件加载成功
  任务过滤列表: ['conv-26', 'conv-30', 'conv-41', 'conv-42', 'conv-43', 'conv-44', 'conv-47', 'conv-48']
  共 8 个任务

✓ DataLoader.get_tasks() 支持任务过滤
  策略: PreInsert_Mem0g_none
  未过滤: 10 个任务
  过滤后: 8 个任务
  过滤掉: {'conv-50', 'conv-49'}

✓ DataLoader.iter_tasks() 支持任务过滤
  迭代未过滤: 10 个TaskData
  迭代过滤后: 8 个TaskData

✓ 所有实验的任务统计:
  PreInsert_Mem0g_none:
    - 实际任务: 10 个
    - 评估任务: 8 个
    - 排除任务: ['conv-49', 'conv-50']
  PreInsert_Mem0g_rewrite_triplet_extract:
    - 实际任务: 10 个
    - 评估任务: 8 个
    - 排除任务: ['conv-49', 'conv-50']
  Additional_Qwen_Mem0g_none:
    - 实际任务: 10 个
    - 评估任务: 8 个
    - 排除任务: ['conv-49', 'conv-50']
  Additional_Qwen_Mem0g_rewrite:
    - 实际任务: 8 个
    - 评估任务: 8 个

======================================================================
✓ 所有验证通过！任务过滤功能正常工作
======================================================================
```

## 影响范围

### 修改的文件 (3个)
1. `benchmarks/evaluation/analysis/config/additional_model_qwen.yaml` - 添加tasks字段
2. `benchmarks/evaluation/analysis/utils/data_loader.py` - 6个方法增强
3. `benchmarks/evaluation/analysis/round_analyzer.py` - 传递tasks_filter

### 新增的文件 (2个)
1. `benchmarks/experiment/script/additional_model_qwen/TASK_FILTERING.md` - 详细文档
2. `benchmarks/experiment/script/additional_model_qwen/TASK_FILTERING_SUMMARY.md` - 本文件

### 更新的文件 (1个)
1. `benchmarks/experiment/script/additional_model_qwen/analyze_qwen_comparison.sh` - 添加说明

## 特性

### 向后兼容
- ✅ `tasks_filter` 默认为 `None`，不影响现有代码
- ✅ 未配置`tasks`字段的配置文件仍正常工作（评估所有任务）
- ✅ 所有修改都是可选参数，不破坏现有API

### 通用性
- ✅ 不仅适用于Qwen实验，可用于任何需要限制评估任务的场景
- ✅ 支持任意任务子集选择
- ✅ 配置驱动，易于调整

### 可观测性
- ✅ 运行时输出任务过滤信息
- ✅ 验证脚本可快速检查过滤效果
- ✅ 日志明确显示评估任务数

## 使用示例

### 运行评估（自动应用任务过滤）

```bash
bash benchmarks/experiment/script/additional_model_qwen/analyze_qwen_comparison.sh
```

### 预期输出

```
======================================================================
  补充实验：LLM模型对比 - PreInsert 策略分析 (D2 Normalization)
======================================================================

评估任务：
  • conv-26, conv-30, conv-41, conv-42, conv-43, conv-44, conv-47, conv-48
  • 共8个任务（为公平对比，所有实验使用相同任务集）

...

======================================================================
开始分析 (4 个策略)
======================================================================

任务过滤: 仅评估 8 个任务: ['conv-26', 'conv-30', 'conv-41', 'conv-42', 'conv-43', 'conv-44', 'conv-47', 'conv-48']

[PreInsert_Mem0g_none]
  F1 Scores: {...}
  ...
```

## 总结

✅ **问题已解决**: 所有实验现在使用相同的8个任务进行评估
✅ **公平对比**: PanGu和Qwen实验在相同数据集上对比
✅ **向后兼容**: 不影响其他实验配置
✅ **通用功能**: 可复用于其他需要任务过滤的场景
✅ **文档完善**: 提供详细说明和验证脚本

现在可以放心运行Qwen评估分析，结果将是公平可靠的对比！
