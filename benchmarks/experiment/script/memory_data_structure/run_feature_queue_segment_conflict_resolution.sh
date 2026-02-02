#!/bin/bash
# Run Memory Data Structure Experiment - Feature Queue Segment Combination
# Dataset: Conflict Resolution (MemAgentBench)
# Usage: bash script/memory_data_structure/run_feature_queue_segment_conflict_resolution.sh

set -e  # Exit on error

# Get absolute path of script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get project root directory (4 levels up from script/memory_data_structure/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
# Python script relative path
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
# Config file path
CONFIG_FILE="$SCRIPT_DIR/../../config/memory_data_structure/conflict_resolution_feature_queue_segment_pipeline.yaml"

# Define all task IDs (Conflict Resolution has only one task_all)
TASK_IDS=(
  "task_all"
)

# Create log directory structure
DATASET="conflict_resolution"
MEMORY_NAME="DataStructure_feature_queue_segment"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "Memory Data Structure Experiment - Feature Queue Segment Combination"
echo "Dataset: Conflict Resolution (MemAgentBench)"
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
  echo "Starting task [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "Log directory: $LOG_DIR"
  echo "--------------------------------------------------------------------"

  # Run task and redirect output to log file (also display on terminal)
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
echo "All tasks completed - DataStructure_feature_queue_segment (Conflict Resolution)"
echo "All logs saved to: $LOG_BASE_DIR"
echo "========================================================================"
