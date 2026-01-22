#!/bin/bash
# ============================================================
# Llama-3.1-8B Backbone 补充实验批量运行脚本
# 用途: 响应ICML审稿人关于"仅Pangu 1B"的评审意见
# 位置: benchmarks/experiment/config/additional_experiments_ds_llama/
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SCRIPT_BASE_DIR="${PROJECT_ROOT}/benchmarks/experiment/script/additional_experiments_ds_llama"
RESULT_DIR="${SCRIPT_DIR}/results"

# 创建结果目录
mkdir -p "${RESULT_DIR}"

# 脚本文件列表（在script目录下）
SCRIPTS=(
    "run_llama_fifo_queue.sh"
    "run_llama_segment.sh"
    "run_llama_inverted_vectorstore.sh"
    "run_llama_lsh_hash.sh"
    "run_llama_feature_queue_segment.sh"
    "run_llama_feature_queue_summary.sh"
    "run_llama_feature_queue_vector.sh"
    "run_llama_feature_summary_vector.sh"
    "run_llama_linknote_graph.sh"
    "run_llama_property_graph.sh"
    "run_llama_semantic_kg.sh"
)

# 日志文件
LOG_FILE="${RESULT_DIR}/experiment_log_$(date +%Y%m%d_%H%M%S).txt"

echo "========================================"
echo "Llama-3.1-8B Backbone 补充实验"
echo "========================================"
echo "脚本数量: ${#SCRIPTS[@]}"
echo "项目根目录: ${PROJECT_ROOT}"
echo "脚本目录: ${SCRIPT_BASE_DIR}"
echo "结果目录: ${RESULT_DIR}"
echo "日志文件: ${LOG_FILE}"
echo "========================================"
echo ""

# 切换到项目根目录
cd "${PROJECT_ROOT}"

# 运行所有脚本
for i in "${!SCRIPTS[@]}"; do
    script="${SCRIPTS[$i]}"
    script_path="${SCRIPT_BASE_DIR}/${script}"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$((i+1))/${#SCRIPTS[@]}] 运行: ${script}" | tee -a "${LOG_FILE}"

    if [ ! -f "${script_path}" ]; then
        echo "  ❌ 脚本文件不存在: ${script_path}" | tee -a "${LOG_FILE}"
        continue
    fi

    # 运行脚本
    if bash "${script_path}" 2>&1 | tee -a "${LOG_FILE}"; then
        echo "  ✅ 完成: ${script}" | tee -a "${LOG_FILE}"
    else
        echo "  ❌ 失败: ${script}" | tee -a "${LOG_FILE}"
    fi

    echo "" | tee -a "${LOG_FILE}"
done

echo "========================================"
echo "实验完成！"
echo "查看日志: ${LOG_FILE}"
echo "========================================"
