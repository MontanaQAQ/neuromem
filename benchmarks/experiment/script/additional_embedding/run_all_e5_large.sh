#!/bin/bash
# 补充实验：运行所有 e5-large-v2 embedding 对比实验
# 使用方法: bash benchmarks/experiment/script/additional_embedding/run_all_e5_large.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================================"
echo "补充实验: e5-large-v2 Embedding 对比实验套件"
echo "========================================================================"
echo ""
echo "实验设置："
echo "  - Embedding模型: intfloat/e5-large-v2 (port 8092, GPU 1)"
echo "  - 数据集: Locomo (D2 Normalization)"
echo "  - 对比组: Mem0g + None vs. Mem0g + Rewrite"
echo ""
echo "请确保 embedding server 已启动："
echo "  HF_ENDPOINT=https://hf-mirror.com python packages/sage-common/src/sage/common/components/sage_embedding/embedding_server.py \\"
echo "    --model intfloat/e5-large-v2 --port 8092 --gpu 1"
echo ""
read -p "按 Enter 键继续，或 Ctrl+C 取消..."
echo ""

# 运行实验1：Mem0g + None + e5-large-v2
echo "========================================================================"
echo "实验 1/2: Mem0g + None + e5-large-v2"
echo "========================================================================"
bash "$SCRIPT_DIR/run_mem0g_none_e5_large.sh"

echo ""
echo "========================================================================"
echo "实验 2/2: Mem0g + Rewrite + e5-large-v2"
echo "========================================================================"
bash "$SCRIPT_DIR/run_mem0g_rewrite_e5_large.sh"

echo ""
echo "========================================================================"
echo "🎉 所有补充实验完成！"
echo "========================================================================"
echo ""
echo "结果目录："
echo "  - Mem0g + None: .sage/output/benchmarks/benchmark_memory/locomo/Additional_Mem0g_none_e5_large"
echo "  - Mem0g + Rewrite: .sage/output/benchmarks/benchmark_memory/locomo/Additional_Mem0g_rewrite_e5_large"
echo ""
echo "下一步："
echo "  1. 运行数据分析脚本"
echo "  2. 生成对比报告"
echo ""
