#!/bin/bash
# ============================================================================
# analyze_llama_comparison.sh
#
# 补充实验：Llama-3-8B 模型下 PostRetrieval 策略对比分析
# 对比：Mem0g + Augment vs. Mem0g + Multi-query (D5 Integration)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

echo "========================================================================"
echo "  补充实验：LLM模型对比 - PostRetrieval 策略分析"
echo "========================================================================"
echo ""
echo "LLM模型对比："
echo "  • PanGu-1B (原始实验)"
echo "  • Llama-3-8B (补充实验)"
echo ""
echo "策略对比："
echo "  • Mem0g + Augment       (结果增强)"
echo "  • Mem0g + Multi-query   (多查询检索)"
echo ""

# 切换到 evaluation/analysis 目录
cd "$PROJECT_ROOT/benchmarks/evaluation/analysis" || exit 1

# 输出目录
OUTPUT_DIR=".sage/benchmarks/benchmark_memory/locomo/output/round_analysis_additional_model_llama"

# 分析策略列表（包含PanGu和Llama两组实验）
STRATEGIES=(
    "PostRetrieval_Mem0g_augment"
    "PostRetrieval_Mem0g_multi_query"
    "Additional_Llama_Mem0g_augment"
    "Additional_Llama_Mem0g_multi_query"
)

# 构建路径参数
PATHS=""
for strategy in "${STRATEGIES[@]}"; do
    PATHS="$PATHS $strategy"
done

CMD="python round_analyzer.py --config additional_model_llama --path $PATHS --output-dir $OUTPUT_DIR"

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
echo "  1. Augment vs Multi-query 在 F1 分数上的差异"
echo "  2. 两种策略的检索时间对比"
echo "  3. Llama-3-8B 模型对 PostRetrieval 策略的影响"
echo ""
