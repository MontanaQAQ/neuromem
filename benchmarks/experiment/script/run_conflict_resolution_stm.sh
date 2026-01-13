#!/bin/bash
# Run Conflict Resolution memory experiment - Short Term Memory (STM) batch test
# Usage: bash script/run_conflict_resolution_stm.sh

set -e  # Exit immediately on error

# Get absolute path of script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get project root directory (from script/ up 3 levels to neuromem/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# Python script relative path
PYTHON_SCRIPT="$SCRIPT_DIR/../memory_test_pipeline.py"
# Configuration file path
CONFIG_FILE="$SCRIPT_DIR/../config/conflict_resolution_short_term_memory_pipeline.yaml"

# Define all task IDs
TASK_IDS=(
  "task_all"
)

# Create log directory structure
DATASET="conflict_resolution"
MEMORY_NAME="stm"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "Conflict Resolution Memory Experiment - Short Term Memory (STM) Batch Test"
echo "========================================================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo "Python script: $(realpath "$PYTHON_SCRIPT")"
echo "Config file: $(realpath "$CONFIG_FILE")"
echo "Total tasks: ${#TASK_IDS[@]}"
echo ""

# Change to project root directory
cd "$PROJECT_ROOT"

# Run all tasks sequentially
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))

  # Generate log directory with timestamp
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"

  echo "--------------------------------------------------------------------"
  echo "🚀 Starting task [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "📝 Log directory: $LOG_DIR"
  echo "--------------------------------------------------------------------"
  echo ""

  # Run experiment and redirect output to log file
  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ Task $TASK_ID completed, logs saved to: $LOG_DIR"
  else
    echo "❌ Task $TASK_ID failed, logs saved to: $LOG_DIR"
    exit 1
  fi
  echo ""
done

echo "========================================================================"
echo "? All tasks completed! Total: ${#TASK_IDS[@]} tasks"
echo "========================================================================"
