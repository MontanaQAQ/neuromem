#!/bin/bash
# ============================================================================
# datastructure_conflict_resolution_evaluate.sh
#
# Conflict Resolution DataStructure Evaluation Script
# Automatically discovers and analyzes all DataStructure_* directories
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$EVAL_DIR/../.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

echo "========================================"
echo "  Conflict Resolution DataStructure Evaluation"
echo "========================================"
echo ""

# Default parameters
PREFIX="DataStructure_"
VALIDATE_ONLY=""
SPECIFIC_PATHS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --validate-only)
            VALIDATE_ONLY="--validate-only"
            shift
            ;;
        --path)
            shift
            SPECIFIC_PATHS="--path"
            while [[ $# -gt 0 && ! $1 == --* ]]; do
                SPECIFIC_PATHS="$SPECIFIC_PATHS $1"
                shift
            done
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --validate-only    Only validate data, do not run analysis"
            echo "  --path <dirs...>   Specify directories to analyze (multiple allowed)"
            echo "  --help             Show help information"
            echo ""
            echo "Examples:"
            echo "  $0                                                 # Analyze all DataStructure_* directories"
            echo "  $0 --validate-only                                 # Validation only"
            echo "  $0 --path DataStructure_fifo_queue                 # Analyze specific directory"
            echo "  $0 --path DataStructure_fifo_queue DataStructure_lsh_hash  # Analyze multiple directories"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Switch to analysis directory for execution
cd "$EVAL_DIR/analysis" || exit 1

# Build command - specify independent output directory
OUTPUT_DIR=".sage/benchmarks/benchmark_memory/conflict_resolution/output/round_analysis_datastructure"

if [[ -n "$SPECIFIC_PATHS" ]]; then
    CMD="python round_analyzer.py --config conflict_resolution $SPECIFIC_PATHS --output-dir $OUTPUT_DIR $VALIDATE_ONLY"
else
    CMD="python round_analyzer.py --config conflict_resolution --all --prefix $PREFIX --output-dir $OUTPUT_DIR $VALIDATE_ONLY"
fi

echo "Executing: $CMD"
echo ""

# Run analysis
eval $CMD

echo ""
echo "========================================"
echo "  ? Evaluation Complete"
echo "========================================"
