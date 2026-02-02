#!/bin/bash
# Llama Run - Mem0g Locomo PostRetrieval - augment

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../../memory_test_pipeline.py"
CONFIG_FILE="$SCRIPT_DIR/../../../config/additional_experiments_ds_llama/llama_context_integration_mechanism/Mem0g_locomo_augment_post_retrieval_pipeline.yaml"

TASK_IDS=(
  "conv-26"
)

DATASET="locomo"
MEMORY_NAME="PostRetrieval_Mem0g_augment_Llama"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

cd "$PROJECT_ROOT"

for TASK_ID in "${TASK_IDS[@]}"; do
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"
  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"
  test ${PIPESTATUS[0]} -eq 0
done
