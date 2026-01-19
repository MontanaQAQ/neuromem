#!/bin/bash
# 运行 Longmemeval 长轮对话记忆实验 - A-Mem 批量测试
# 使用方法: bash script/primitive_memory_model/run_amem_longmemeval.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../../config/primitive_memory_model/longmemeval_amem_pipeline.yaml"

TASK_IDS=("group-1" "group-2" "group-3")

DATASET="longmemeval"
MEMORY_NAME="A-Mem"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "Longmemeval 长轮对话记忆实验 - A-Mem 批量测试"
echo "========================================================================"
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $(realpath "$PYTHON_SCRIPT")"
echo "配置文件: $(realpath "$CONFIG_FILE")"
echo "日志目录: $LOG_BASE_DIR"
echo "总任务数: ${#TASK_IDS[@]}"

cd "$PROJECT_ROOT"

for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"

  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"
  if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "❌ 任务 $TASK_ID 失败"
    exit 1
  fi
done

echo "🎉 所有任务执行完毕 - A-Mem"
