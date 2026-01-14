#!/bin/bash
# Run MemoryOS Locomo PostRetrieval Experiment - multi_query
# Usage: bash script/post_retrieval_strategy/run_memoryos_locomo_multi_query.sh

set -e  # Exit immediately on error

# Get absolute path of script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get project root directory (4 levels up from script/post_retrieval_strategy/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
# Python script relative path
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
# Configuration file path
CONFIG_FILE="$SCRIPT_DIR/../../config/post_retrieval_strategy/MemoryOS_locomo_multi_query_post_retrieval_pipeline.yaml"

# Define all task IDs
TASK_IDS=(
  "conv-26"
  # "conv-30"
  # "conv-41"
  # "conv-42"
  # "conv-43"
  # "conv-44"
  # "conv-47"
  # "conv-48"
  # "conv-49"
  # "conv-50"
)

# Create log directory structure
DATASET="locomo"
MEMORY_NAME="post_retrieval_multi_query_MemoryOS"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "MemoryOS Locomo PostRetrieval Experiment - multi_query"
echo "========================================================================"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Python Script: $(realpath "$PYTHON_SCRIPT")"
echo "Config File: $(realpath "$CONFIG_FILE")"
echo "Log Directory: $LOG_BASE_DIR"
echo "Total Tasks: ${#TASK_IDS[@]}"
echo ""

# Change to project root directory
cd "$PROJECT_ROOT"

# Run all tasks sequentially
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))

  # Generate timestamped log filename
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"

  echo "--------------------------------------------------------------------"
  echo "Start Task [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "Log Directory: $LOG_DIR"
  echo "--------------------------------------------------------------------"

  # Run task and redirect output to log file (also display in terminal)
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
echo "All tasks completed - post_retrieval_multi_query_MemoryOS"
echo "All logs saved to: $LOG_BASE_DIR"
echo "========================================================================"
