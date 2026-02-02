#!/bin/bash
# 运行 Mem0g PostInsert 实验 - link_evolution (专属策略)
# 使用方法: bash script/consolidation_policy/run_mem0g_locomo_link_evolution.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../../config/consolidation_policy/Mem0g_locomo_link_evolution_post_insert_pipeline.yaml"

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
MEMORY_NAME="PostInsert_Mem0g_link_evolution"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "Mem0g PostInsert 实验 - link_evolution (专属策略)"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "配置文件: $(realpath "$CONFIG_FILE")"
echo "日志目录: $LOG_BASE_DIR"
echo "总任务数: ${#TASK_IDS[@]}"
echo ""

cd "$PROJECT_ROOT"

for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"

  echo "--------------------------------------------------------------------"
  echo "🚀 开始运行任务 [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "📝 日志目录: $LOG_DIR"
  echo "--------------------------------------------------------------------"

  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ 任务 $TASK_ID 完成"
  else
    echo "❌ 任务 $TASK_ID 失败"
    exit 1
  fi
  echo ""
done

echo "========================================================================"
echo "🎉 所有任务执行完毕 - $MEMORY_NAME"
echo "📁 日志目录: $LOG_BASE_DIR"
echo "========================================================================"
