#!/bin/bash
# 补充实验：运行所有 Llama-3-8B 模型对比实验
# 使用方法: bash benchmarks/experiment/script/additional_model_llama/run_all_llama.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================================"
echo "补充实验: Llama-3-8B 模型对比实验套件"
echo "========================================================================"
echo ""
echo "实验设置："
echo "  - LLM模型: meta-llama/Meta-Llama-3-8B-Instruct (sage2:8001)"
echo "  - 数据集: Locomo (D5 Integration/PostRetrieval)"
echo "  - 对比组: Mem0g + Augment vs. Mem0g + Multi-query"
echo ""
echo "请确保 Llama 服务已启动："
echo "  Base URL: http://sage2:8001/v1"
echo "  Model: meta-llama/Meta-Llama-3-8B-Instruct"
echo ""
read -p "按 Enter 键继续，或 Ctrl+C 取消..."
echo ""

# 运行实验1：Mem0g + Augment + Llama
echo "========================================================================"
echo "实验 1/2: Mem0g + Augment + Llama-3-8B"
echo "========================================================================"
bash "$SCRIPT_DIR/run_mem0g_augment_llama.sh"

echo ""
echo "========================================================================"
echo "实验 2/2: Mem0g + Multi-query + Llama-3-8B"
echo "========================================================================"
bash "$SCRIPT_DIR/run_mem0g_multi_query_llama.sh"

echo ""
echo "========================================================================"
echo "🎉 所有补充实验完成！"
echo "========================================================================"
echo ""
echo "结果目录："
echo "  - Mem0g + Augment:     .sage/output/benchmarks/benchmark_memory/locomo/PostRetrieval_Mem0g_augment_Llama"
echo "  - Mem0g + Multi-query: .sage/output/benchmarks/benchmark_memory/locomo/PostRetrieval_Mem0g_multi_query_Llama"
echo ""
echo "下一步："
echo "  1. 运行数据分析脚本: bash benchmarks/experiment/script/additional_model_llama/analyze_llama_comparison.sh"
echo "  2. 查看快速对比: python benchmarks/experiment/script/additional_model_llama/quick_compare.py"
echo ""
