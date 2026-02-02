#!/bin/bash
# ============================================================================
# analyze_e5_large_comparison.sh
#
# 补充实验：e5-large-v2 vs bge-m3 对比分析
# 对比：Mem0g + None / Rewrite 在两种 embedding 模型下的表现
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 从 additional_embedding -> script -> experiment -> benchmarks -> neuromem (4层)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

echo "========================================================================"
echo "  补充实验：Embedding 模型对比分析"
echo "========================================================================"
echo ""
echo "对比组："
echo "  1. BAAI/bge-m3      (原始实验)"
echo "  2. intfloat/e5-large-v2 (补充实验)"
echo ""
echo "策略："
echo "  • Mem0g + None"
echo "  • Mem0g + Rewrite"
echo ""

# 切换到 evaluation/analysis 目录
cd "$PROJECT_ROOT/benchmarks/evaluation/analysis" || exit 1

# 输出目录
OUTPUT_DIR=".sage/benchmarks/benchmark_memory/locomo/output/round_analysis_additional_embedding"

# 分析策略列表 (4个：2个原始 + 2个补充)
STRATEGIES=(
    "PreInsert_Mem0g_none"                    # bge-m3 + None
    "Additional_Mem0g_none_e5_large"          # e5-large-v2 + None
    "PreInsert_Mem0g_rewrite_triplet_extract" # bge-m3 + Rewrite
    "Additional_Mem0g_rewrite_e5_large"       # e5-large-v2 + Rewrite
)

# 构建路径参数
PATHS=""
for strategy in "${STRATEGIES[@]}"; do
    PATHS="$PATHS $strategy"
done

CMD="python round_analyzer.py --config additional_embedding --path $PATHS --output-dir $OUTPUT_DIR"

echo "执行: $CMD"
echo ""

# 运行分析
eval $CMD

echo ""
echo "========================================================================"
echo "✓ 分析完成！"
echo "========================================================================"
echo ""
echo "结果目录: $OUTPUT_DIR"
echo ""
echo "生成文件："
echo "  • comparison_f1.png                    - F1 分数对比图"
echo "  • comparison_cost_effectiveness.png    - 成本效益对比图"
echo "  • f1_scores.csv                        - F1 分数数据表"
echo "  • analysis_report.md                   - 详细分析报告"
echo ""
echo "关键对比："
echo "  1. bge-m3 vs e5-large-v2 在 None 策略下的差异"
echo "  2. bge-m3 vs e5-large-v2 在 Rewrite 策略下的差异"
echo "  3. 两种 embedding 模型对 PreInsert 策略的影响"
echo ""
