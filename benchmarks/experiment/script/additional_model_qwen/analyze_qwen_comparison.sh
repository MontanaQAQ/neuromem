#!/bin/bash
# ============================================================================
# analyze_qwen_comparison.sh
#
# 补充实验：Qwen-Plus 模型下 PreInsert 策略对比分析
# 对比：Mem0g + None vs. Mem0g + Rewrite (D2 Normalization)
#
# 注意：由于硬件限制，Qwen实验仅运行了8个任务（conv-26,30,41-44,47-48）
#       为了公平对比，所有实验（包括PanGu基准）都将仅评估这8个任务
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

echo "========================================================================"
echo "  补充实验：LLM模型对比 - PreInsert 策略分析 (D2 Normalization)"
echo "========================================================================"
echo ""
echo "LLM模型对比："
echo "  • PanGu-1B (原始实验)"
echo "  • Qwen-Plus-2025-12-01 (补充实验)"
echo ""
echo "策略对比："
echo "  • Mem0g + None       (无预处理)"
echo "  • Mem0g + Rewrite    (三元组抽取)"
echo ""
echo "评估任务："
echo "  • conv-26, conv-30, conv-41, conv-42, conv-43, conv-44, conv-47, conv-48"
echo "  • 共8个任务（为公平对比，所有实验使用相同任务集）"
echo ""

# 切换到 evaluation/analysis 目录
cd "$PROJECT_ROOT/benchmarks/evaluation/analysis" || exit 1

# 输出目录
OUTPUT_DIR=".sage/benchmarks/benchmark_memory/locomo/output/round_analysis_additional_model_qwen"

# 分析策略列表（包含PanGu和Qwen两组实验）
STRATEGIES=(
    "PreInsert_Mem0g_none"
    "PreInsert_Mem0g_rewrite_triplet_extract"
    "Additional_Qwen_Mem0g_none"
    "Additional_Qwen_Mem0g_rewrite"
)

# 构建路径参数
PATHS=""
for strategy in "${STRATEGIES[@]}"; do
    PATHS="$PATHS $strategy"
done

CMD="python round_analyzer.py --config additional_model_qwen --path $PATHS --output-dir $OUTPUT_DIR"

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
echo "  1. LLM模型对F1分数的影响 (PanGu vs Qwen)"
echo "  2. PreInsert策略对比 (None vs Rewrite)"
echo "  3. 模型-策略组合的最优选择"
echo "  4. 三元组提取质量分析"
echo ""
