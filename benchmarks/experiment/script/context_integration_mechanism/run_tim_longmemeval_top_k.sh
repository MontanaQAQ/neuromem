#!/bin/bash
# Run TiM Longmemeval PostRetrieval Experiment - top_k
# Usage: bash script/context_integration_mechanism/run_tim_longmemeval_top_k.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../../config/context_integration_mechanism/TiM_longmemeval_top_k_post_retrieval_pipeline.yaml"

TASK_IDS=("group-1" "group-2" "group-3")

DATASET="longmemeval"
MEMORY_NAME="PostRetrieval_TiM_top_k"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "TiM Longmemeval PostRetrieval Experiment - top_k"
echo "========================================================================"
echo "Project Root: $PROJECT_ROOT"
echo "Python Script: $(realpath "$PYTHON_SCRIPT")"
echo "Config File: $(realpath "$CONFIG_FILE")"
echo "Log Directory: $LOG_BASE_DIR"
echo "Total Tasks: ${#TASK_IDS[@]}"

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
  echo "Log Directory: $LOG_DIR"
  echo "--------------------------------------------------------------------"

  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "Task $TASK_ID completed, logs saved to: $LOG_DIR"
  else
    echo "Task $TASK_ID failed, logs saved to: $LOG_DIR"
    exit 1
  fi
  echo ""
done

echo "========================================================================"
echo "All tasks completed - post_retrieval_top_k_TiM"
echo "All logs saved to: $LOG_BASE_DIR"
echo "========================================================================"
