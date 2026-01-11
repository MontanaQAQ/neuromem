#!/bin/bash
# 运行 Normalization Strategy - MemoryOS transform_summarize pre_insert
# 使用方法: bash script/normalization_strategy/run_MemoryOS_locomo_transform_summarize_pre_insert_pipeline.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../../config/normalization_strategy/MemoryOS_locomo_transform_summarize_pre_insert_pipeline.yaml"

TASK_IDS=(
  "conv-42"
  "conv-43"
  "conv-48"
  "conv-49"
  "conv-50"
)

DATASET="locomo"
DATE=$(date +%Y%m%d)
MEMORY_NAME="MemoryOS-transform-summarize"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$DATE/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "Normalization Strategy: MemoryOS transform_summarize pre_insert"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $(realpath "$PYTHON_SCRIPT")"
echo "配置文件: $(realpath "$CONFIG_FILE")"
echo "日志目录: $LOG_BASE_DIR"
echo "总任务数: ${#TASK_IDS[@]}"
echo ""

cd "$PROJECT_ROOT"

for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))
  TIMESTAMP=$(date +%H%M%S)
  LOG_FILE="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}.log"

  echo "--------------------------------------------------------------------"
  echo "🚀 开始运行任务 [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "📝 日志文件: $LOG_FILE"
  echo "--------------------------------------------------------------------"

  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ 任务 $TASK_ID 完成，日志已保存到: $LOG_FILE"
  else
    echo "❌ 任务 $TASK_ID 失败，日志已保存到: $LOG_FILE"
    exit 1
  fi

  echo ""
done

echo "========================================================================"
echo "🎉 所有任务执行完毕 - $MEMORY_NAME"
echo "📁 所有日志已保存到: $LOG_BASE_DIR"
echo "========================================================================"
