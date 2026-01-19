#!/bin/bash
# 运行 Longmemeval 长轮对话记忆实验 - SeCom 批量测试

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../../config/primitive_memory_model/longmemeval_secom_pipeline.yaml"

TASK_IDS=("group-1" "group-2" "group-3")

DATASET="longmemeval"
MEMORY_NAME="SeCom"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "Longmemeval - SeCom 批量测试"
echo "配置文件: $(realpath "$CONFIG_FILE")"

cd "$PROJECT_ROOT"
for TASK_ID in "${TASK_IDS[@]}"; do
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"
  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"
  test ${PIPESTATUS[0]} -eq 0 || exit 1
done

echo "完成 - SeCom"
