#!/bin/bash
# ============================================================================
# pre_retrieval_locomo_evaluate.sh
#
# LoCoMo PreRetrieval实验评估脚本
# 自动发现并分析所有PreRetrieval_*目录
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$EVAL_DIR/../.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

echo "========================================"
echo "  LoCoMo PreRetrieval 评估"
echo "========================================"
echo ""

# 默认参数
PREFIX="PreRetrieve_"
VALIDATE_ONLY=""
SPECIFIC_PATHS=""

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
            echo "  $0                                              # 分析所有PreRetrieval_*目录"
            echo "  $0 --validate-only                              # 仅验证"
            echo "  $0 --path PreRetrieval_MemoryOS_embedding       # 分析指定目录"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 切换到analysis目录运行
cd "$EVAL_DIR/analysis" || exit 1

# 构建命令 - 指定独立的输出目录
OUTPUT_DIR=".sage/benchmarks/benchmark_memory/locomo/output/round_analysis_pre_retrieval"

if [[ -n "$SPECIFIC_PATHS" ]]; then
    CMD="python round_analyzer.py --config locomo $SPECIFIC_PATHS --output-dir $OUTPUT_DIR $VALIDATE_ONLY"
else
    CMD="python round_analyzer.py --config locomo --all --prefix $PREFIX --output-dir $OUTPUT_DIR $VALIDATE_ONLY"
fi

echo "执行: $CMD"
echo ""

# 运行分析
eval $CMD

echo ""
echo "========================================"
echo "  ✓ 评估完成"
echo "========================================"
