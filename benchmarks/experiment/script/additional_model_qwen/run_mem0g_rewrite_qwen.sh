#!/bin/bash
# ============================================================================
# run_mem0g_rewrite_qwen.sh
#
# 补充实验：Mem0g + Rewrite (D2 Normalization) + Qwen-Plus
# 使用方法: bash benchmarks/experiment/script/additional_model_qwen/run_mem0g_rewrite_qwen.sh
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$PROJECT_ROOT/benchmarks/experiment/memory_test_pipeline.py"
CONFIG_FILE="$PROJECT_ROOT/benchmarks/experiment/config/additional_experiments_ds_qwen/qwen_triple_extraction/Mem0g_locomo_rewrite_qwen.yaml"

# 定义所有任务 ID
TASK_IDS=(
  "conv-26"
  "conv-30"
  "conv-41"
  "conv-42"
  "conv-43"
  "conv-44"
  "conv-47"
  "conv-48"
  "conv-49"
  "conv-50"
)

DATASET="locomo"
MEMORY_NAME="Additional_Qwen_Mem0g_rewrite"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "补充实验: Mem0g + Rewrite (Triple Extract) + Qwen-Plus-2025-12-01"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "配置文件: $CONFIG_FILE"
echo "日志目录: $LOG_BASE_DIR"
echo ""
echo "任务列表: ${TASK_IDS[@]}"
echo "========================================================================"
echo ""

# 遍历所有任务
for task_id in "${TASK_IDS[@]}"; do
  echo "----------------------------------------"
  echo "开始运行任务: $task_id"
  echo "----------------------------------------"

  LOG_FILE="$LOG_BASE_DIR/${task_id}.log"

  cd "$PROJECT_ROOT" || exit 1

  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python "$PYTHON_SCRIPT" \
    --config "$CONFIG_FILE" \
    --task_id "$task_id" \
    2>&1 | tee "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✓ 任务 $task_id 完成"
  else
    echo "✗ 任务 $task_id 失败"
    exit 1
  fi

  echo ""
done

echo "========================================================================"
echo "✓ 所有任务完成！"
echo "========================================================================"
echo ""
echo "日志目录: $LOG_BASE_DIR"
echo ""
