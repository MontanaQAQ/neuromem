#!/bin/bash
# ============================================================================
# run_all_qwen.sh
#
# 补充实验：批量运行所有 Qwen-Plus D2 实验
# 使用方法: bash benchmarks/experiment/script/additional_model_qwen/run_all_qwen.sh
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================================"
echo "  补充实验：Qwen-Plus D2 (Normalization) 批量运行"
echo "========================================================================"
echo ""
echo "实验列表："
echo "  1. Mem0g + None + Qwen-Plus"
echo "  2. Mem0g + Rewrite (Triple Extract) + Qwen-Plus"
echo ""
echo "========================================================================"
echo ""

# 运行 None 实验
echo ">>> 开始实验 1/2: Mem0g + None + Qwen-Plus"
bash "$SCRIPT_DIR/run_mem0g_none_qwen.sh"

echo ""
echo "========================================================================"
echo ""

# 运行 Rewrite 实验
echo ">>> 开始实验 2/2: Mem0g + Rewrite + Qwen-Plus"
bash "$SCRIPT_DIR/run_mem0g_rewrite_qwen.sh"

echo ""
echo "========================================================================"
echo "✓ 所有实验完成！"
echo "========================================================================"
echo ""
echo "结果目录："
echo "  • .sage/output/benchmarks/benchmark_memory/locomo/Additional_Qwen_Mem0g_none"
echo "  • .sage/output/benchmarks/benchmark_memory/locomo/Additional_Qwen_Mem0g_rewrite"
echo ""
echo "下一步："
echo "  运行分析脚本："
echo "    bash benchmarks/experiment/script/additional_model_qwen/analyze_qwen_comparison.sh"
echo ""
