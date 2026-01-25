#!/usr/bin/env bash
# ============================================================================
# post_retrieval_locomo_llama_evaluate.sh
#
# LoCoMo Llama PostRetrieval 实验评估脚本
# 逻辑与 post_retrieval_locomo_evaluate.sh 一致，仅调整扫描目录前缀
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$EVAL_DIR/../.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

echo "========================================"
echo "  LoCoMo Llama PostRetrieval 评估"
echo "========================================"
echo ""

# 默认参数（更新：改用通用前缀 + 末尾 _Llama 过滤）
PREFIX="PostRetrieval_"
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
            echo "  $0                                               # 分析所有Llama_PostRetrieval_*目录"
            echo "  $0 --validate-only                               # 仅验证"
            echo "  $0 --path Llama_PostRetrieval_MemoryOS_multi_query  # 分析指定目录"
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

# 构建命令 - Llama 独立输出目录（避免与非 Llama 混写）
OUTPUT_DIR=".sage/benchmarks/benchmark_memory/locomo/output/round_analysis_post_retrieval_llama"

# 基础数据目录（与 round_analyzer 的默认一致）
BASE_DIR="$PROJECT_ROOT/.sage/benchmarks/benchmark_memory/locomo"

if [[ -n "$SPECIFIC_PATHS" ]]; then
    CMD="python round_analyzer.py --config locomo $SPECIFIC_PATHS --output-dir $OUTPUT_DIR $VALIDATE_ONLY"
else
    # 同时支持两种命名：
    # 1) 新命名：以 PREFIX 开头且以 _Llama 结尾，如 PostRetrieval_Mem0g_augment_Llama
    # 2) 旧/备用命名：以 Llama_ 前缀且包含 PostRetrieval_，如 Llama_PostRetrieval_MemoryOS_semantic
    mapfile -t LLAMA_DIRS < <(ls -1 "$BASE_DIR" 2>/dev/null | grep -E "^("${PREFIX}".*_Llama|Llama_${PREFIX}.*)" || true)

    if [[ ${#LLAMA_DIRS[@]} -eq 0 ]]; then
        echo "未找到以 '${PREFIX}*' 且以 '_Llama' 结尾的目录于 $BASE_DIR"
        echo "提示：确保实验的 memory_name 使用 'PostRetrieval_<System>_<Strategy>_Llama' 命名"
        exit 1
    fi

    # 在基础目录下创建临时别名目录（去掉 _Llama 或 Llama_ 前缀）
    TMP_ALIAS_DIR="$BASE_DIR/.tmp_llama_alias"
    rm -rf "$TMP_ALIAS_DIR"
    mkdir -p "$TMP_ALIAS_DIR"

    SANITIZED_NAMES=()
    for d in "${LLAMA_DIRS[@]}"; do
        if [[ "$d" == *_Llama ]]; then
            sanitized="${d%_Llama}"
        elif [[ "$d" == Llama_* ]]; then
            sanitized="${d#Llama_}"
        else
            sanitized="$d"
        fi
        # 创建符号链接：别名目录/去前后缀 -> 原目录
        ln -snf "$BASE_DIR/$d" "$TMP_ALIAS_DIR/$sanitized"
        SANITIZED_NAMES+=("$sanitized")
    done

    # 使用别名目录作为 base-dir，并传入去前后缀后的目录名
    PATH_ARGS="--path ${SANITIZED_NAMES[*]}"
    CMD="python round_analyzer.py --config locomo $PATH_ARGS --base-dir \"$TMP_ALIAS_DIR\" --output-dir $OUTPUT_DIR $VALIDATE_ONLY"
fi

echo "执行: $CMD"
echo ""

# 运行分析
eval $CMD

echo ""
echo "========================================"
echo "  ✓ Llama PostRetrieval 评估完成"
echo "========================================"
