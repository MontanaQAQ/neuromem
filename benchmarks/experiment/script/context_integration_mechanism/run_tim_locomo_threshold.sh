#!/bin/bash
# Run TiM Locomo PostRetrieve Experiment - threshold (context integration)
# Usage: bash script/context_integration_mechanism/run_tim_locomo_threshold.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../../config/context_integration_mechanism/TiM_locomo_threshold_post_retrieval.yaml"

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
MEMORY_NAME="PostRetrieve_TiM_threshold"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "TiM Locomo PostRetrieve Experiment - threshold"
echo "========================================================================"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Config File: $(realpath "$CONFIG_FILE")"
echo "Log Directory: $LOG_BASE_DIR"
echo "Total Tasks: ${#TASK_IDS[@]}"
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
  echo "Start Task [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "--------------------------------------------------------------------"

  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "Task $TASK_ID completed"
  else
    echo "Task $TASK_ID failed"
    exit 1
  fi
  echo ""
done

echo "========================================================================"
echo "All tasks completed - context_integration_threshold_TiM"
echo "========================================================================"
