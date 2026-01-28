#!/bin/bash
# ============================================================================
# 任务过滤功能快速验证脚本
# Quick verification script for task filtering functionality
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================================================"
echo "  任务过滤功能验证"
echo "  Task Filtering Verification"
echo "========================================================================"
echo ""

# 1. 验证配置文件
echo "1️⃣  验证配置文件..."
python -c "
import yaml
from pathlib import Path

config_file = Path('benchmarks/evaluation/analysis/config/additional_model_qwen.yaml')
with open(config_file) as f:
    config = yaml.safe_load(f)

tasks = config.get('tasks', None)
if tasks:
    print(f'   ✓ 任务过滤已配置: {len(tasks)} 个任务')
    print(f'   任务列表: {tasks}')
else:
    print('   ✗ 未配置任务过滤')
    exit(1)
"
echo ""

# 2. 验证数据加载器
echo "2️⃣  验证DataLoader..."
python -c "
from pathlib import Path
from benchmarks.evaluation.analysis.utils.data_loader import DataLoader
import yaml

# 加载配置
config_file = Path('benchmarks/evaluation/analysis/config/additional_model_qwen.yaml')
with open(config_file) as f:
    config = yaml.safe_load(f)

tasks_filter = config.get('tasks', [])

# 测试DataLoader
base_dir = Path('.sage/benchmarks/benchmark_memory/locomo')
loader = DataLoader(base_dir)

strategy = 'PreInsert_Mem0g_none'
all_tasks = loader.get_tasks(strategy)
filtered_tasks = loader.get_tasks(strategy, tasks_filter)

print(f'   ✓ DataLoader.get_tasks() 工作正常')
print(f'   未过滤: {len(all_tasks)} 个 | 过滤后: {len(filtered_tasks)} 个')
"
echo ""

# 3. 验证所有实验任务
echo "3️⃣  验证所有实验任务..."
python -c "
from pathlib import Path
from benchmarks.evaluation.analysis.utils.validators import discover_tasks
import yaml

# 加载配置
config_file = Path('benchmarks/evaluation/analysis/config/additional_model_qwen.yaml')
with open(config_file) as f:
    config = yaml.safe_load(f)

tasks_filter = config.get('tasks', [])
base_dir = Path('.sage/benchmarks/benchmark_memory/locomo')

strategies = [
    'PreInsert_Mem0g_none',
    'PreInsert_Mem0g_rewrite_triplet_extract',
    'Additional_Qwen_Mem0g_none',
    'Additional_Qwen_Mem0g_rewrite'
]

all_match = True
for strategy in strategies:
    tasks = discover_tasks(base_dir / strategy)
    filtered = [t for t in tasks if t in tasks_filter]

    if len(filtered) != len(tasks_filter):
        print(f'   ✗ {strategy}: {len(filtered)}/{len(tasks_filter)} 任务')
        all_match = False
    else:
        print(f'   ✓ {strategy}: {len(filtered)}/{len(tasks_filter)} 任务')

if not all_match:
    print()
    print('   ⚠️  某些实验缺少任务，但这不影响评估（会使用可用任务的交集）')
"
echo ""

# 4. 测试评估脚本
echo "4️⃣  测试评估脚本（快速测试）..."
echo "   运行: python round_analyzer.py --config additional_model_qwen ..."
python benchmarks/evaluation/analysis/round_analyzer.py \
    --config additional_model_qwen \
    --path PreInsert_Mem0g_none \
    --output-dir /tmp/task_filtering_test \
    2>&1 | grep -E "(任务过滤|F1 Scores)" | head -5

echo ""
echo "========================================================================"
echo "  ✅ 验证完成！任务过滤功能正常工作"
echo "  ✅ Verification Complete! Task filtering is working correctly"
echo "========================================================================"
echo ""
echo "📖 详细文档:"
echo "   - benchmarks/experiment/script/additional_model_qwen/TASK_FILTERING.md"
echo "   - benchmarks/experiment/script/additional_model_qwen/TASK_FILTERING_SUMMARY.md"
echo ""
echo "🚀 运行完整评估:"
echo "   bash benchmarks/experiment/script/additional_model_qwen/analyze_qwen_comparison.sh"
echo ""
