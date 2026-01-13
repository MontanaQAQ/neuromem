#!/bin/bash
# ============================================================
# 全实验批量运行主脚本
# 一键运行所有维度的实验
# ============================================================
#
# 实验维度总览:
#   1. PreRetrieval (query_formulation_strategy) - 既有实验
#   2. PostInsert (consolidation_policy) - 9个配置
#   3. PostRetrieval (result_optimization_strategy) - 9个配置
#   4. DataStructure (memory_data_structure) - 5个配置
#
# 使用方法:
#   bash run_all_experiments.sh              # 运行所有新实验
#   bash run_all_experiments.sh post_insert  # 仅运行 PostInsert
#   bash run_all_experiments.sh post_retrieval # 仅运行 PostRetrieval
#   bash run_all_experiments.sh data_structure # 仅运行数据结构
#
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 定义子脚本路径
POST_INSERT_SCRIPT="$SCRIPT_DIR/consolidation_policy/run_all_post_insert.sh"
POST_RETRIEVAL_SCRIPT="$SCRIPT_DIR/result_optimization_strategy/run_all_post_retrieval.sh"
DATA_STRUCTURE_SCRIPT="$SCRIPT_DIR/memory_data_structure/run_all_data_structure.sh"

print_header() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                     NeuroMem 记忆实验套件                          ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📌 项目路径: $PROJECT_ROOT"
    echo "📌 运行时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
}

print_summary() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                       实验维度说明                                 ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║  维度                    | 配置数 | 基底模型                       ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║  PostInsert (D3)        |   9   | TiM, MemoryOS, Mem0g          ║"
    echo "║  PostRetrieval (D5)     |   9   | TiM, MemoryOS, Mem0g          ║"
    echo "║  DataStructure (D1)     |   5   | 统一操作配置                    ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
}

run_post_insert() {
    echo "🚀 启动 PostInsert 实验..."
    if [ -f "$POST_INSERT_SCRIPT" ]; then
        bash "$POST_INSERT_SCRIPT"
    else
        echo "❌ 脚本不存在: $POST_INSERT_SCRIPT"
        return 1
    fi
}

run_post_retrieval() {
    echo "🚀 启动 PostRetrieval 实验..."
    if [ -f "$POST_RETRIEVAL_SCRIPT" ]; then
        bash "$POST_RETRIEVAL_SCRIPT"
    else
        echo "❌ 脚本不存在: $POST_RETRIEVAL_SCRIPT"
        return 1
    fi
}

run_data_structure() {
    echo "🚀 启动 DataStructure 实验..."
    if [ -f "$DATA_STRUCTURE_SCRIPT" ]; then
        bash "$DATA_STRUCTURE_SCRIPT"
    else
        echo "❌ 脚本不存在: $DATA_STRUCTURE_SCRIPT"
        return 1
    fi
}

# 主逻辑
print_header

EXPERIMENT_TYPE="${1:-all}"

case "$EXPERIMENT_TYPE" in
    "post_insert"|"pi"|"consolidation")
        print_summary
        run_post_insert
        ;;
    "post_retrieval"|"pr"|"optimization")
        print_summary
        run_post_retrieval
        ;;
    "data_structure"|"ds"|"structure")
        print_summary
        run_data_structure
        ;;
    "all")
        print_summary
        echo "⏳ 开始运行所有实验..."
        echo ""

        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "                    阶段 1/3: PostInsert 实验"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        run_post_insert

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "                    阶段 2/3: PostRetrieval 实验"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        run_post_retrieval

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "                    阶段 3/3: DataStructure 实验"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        run_data_structure
        ;;
    *)
        echo "❓ 未知实验类型: $EXPERIMENT_TYPE"
        echo ""
        echo "可用选项:"
        echo "  all            - 运行所有实验"
        echo "  post_insert    - 仅运行 PostInsert 实验"
        echo "  post_retrieval - 仅运行 PostRetrieval 实验"
        echo "  data_structure - 仅运行 DataStructure 实验"
        exit 1
        ;;
esac

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 所有实验已完成! 🎉                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 日志位置: $PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/"
echo "📅 日期: $(date +%Y%m%d)"
echo ""
