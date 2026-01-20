#!/bin/bash
# ============================================================================
# datastructure_longmemeval_evaluate.sh
#
# LongMemEval DataStructure 实验评估脚本
# 自动发现并分析 .sage/benchmarks/benchmark_memory/longmemeval 下所有 DataStructure_* 目录
# 说明：沿用 round_analyzer 的 locomo 配置，但通过 --base-dir 与 --output-dir 指向 longmemeval 数据
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$EVAL_DIR/../.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

echo "========================================"
echo "  LongMemEval DataStructure 评估"
echo "========================================"
echo ""

# 默认参数
PREFIX="DataStructure_"
VALIDATE_ONLY=""
SPECIFIC_PATHS=""

# Paths for longmemeval dataset
LONG_BASE_DIR=".sage/benchmarks/benchmark_memory/longmemeval"
OUTPUT_DIR=".sage/benchmarks/benchmark_memory/longmemeval/output/round_analysis_datastructure"

# 解析参数
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
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --validate-only    仅验证数据，不执行分析"
            echo "  --path <dirs...>   指定要分析的目录（可多个）"
            echo "  --help             显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                                                 # 分析所有DataStructure_*目录"
            echo "  $0 --validate-only                                 # 仅验证"
            echo "  $0 --path DataStructure_fifo_queue                 # 分析指定目录"
            echo "  $0 --path DataStructure_fifo_queue DataStructure_lsh_hash  # 分析多个目录"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 切换到 analysis 目录运行
cd "$EVAL_DIR/analysis" || exit 1

# 构建命令 - 指定 longmemeval 的 base-dir 与独立的输出目录
if [[ -n "$SPECIFIC_PATHS" ]]; then
    CMD="python round_analyzer.py --config locomo --base-dir $LONG_BASE_DIR $SPECIFIC_PATHS --output-dir $OUTPUT_DIR $VALIDATE_ONLY"
else
    CMD="python round_analyzer.py --config locomo --base-dir $LONG_BASE_DIR --all --prefix $PREFIX --output-dir $OUTPUT_DIR $VALIDATE_ONLY"
fi

echo "执行: $CMD"
echo ""

# 运行分析
eval $CMD

echo ""
echo "========================================"
echo "  ✓ 评估完成"
echo "========================================"
