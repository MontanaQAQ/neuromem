#!/bin/bash
# ============================================================
# PostRetrieval 实验批量运行脚本
# 运行所有 PostRetrieval 维度的实验（9个配置）
# 使用方法: bash run_all_post_retrieval.sh
# ============================================================

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
CONFIG_DIR="$SCRIPT_DIR/../../config/result_optimization_strategy"

# 定义所有配置文件
CONFIG_FILES=(
  # TiM 系列
  "TiM_locomo_none_post_retrieval_pipeline.yaml"
  "TiM_locomo_time_weighted_post_retrieval.yaml"
  "TiM_locomo_threshold_post_retrieval.yaml"
  # MemoryOS 系列
  "MemoryOS_locomo_none_post_retrieval_pipeline.yaml"
  "MemoryOS_locomo_time_weighted_post_retrieval.yaml"
  "MemoryOS_locomo_augment_post_retrieval.yaml"
  # Mem0g 系列
  "Mem0g_locomo_none_post_retrieval_pipeline.yaml"
  "Mem0g_locomo_link_expand_post_retrieval.yaml"
  "Mem0g_locomo_threshold_post_retrieval.yaml"
)

# 定义测试任务 ID
TASK_IDS=(
  "conv-26"
  "conv-30"
  "conv-41"
  "conv-42"
  "conv-43"
)

# 创建日志目录
DATASET="locomo"
DATE=$(date +%Y%m%d)
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$DATE/post_retrieval_experiment"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "PostRetrieval 维度实验批量运行"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "配置文件数: ${#CONFIG_FILES[@]}"
echo "测试任务数: ${#TASK_IDS[@]}"
echo "日志目录: $LOG_BASE_DIR"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 遍历所有配置文件
for config_file in "${CONFIG_FILES[@]}"; do
  CONFIG_PATH="$CONFIG_DIR/$config_file"
  MEMORY_NAME=$(basename "$config_file" .yaml)

  echo "--------------------------------------------------------------------"
  echo "🚀 开始运行配置: $config_file"
  echo "--------------------------------------------------------------------"

  # 为每个配置创建日志子目录
  CONFIG_LOG_DIR="$LOG_BASE_DIR/$MEMORY_NAME"
  mkdir -p "$CONFIG_LOG_DIR"

  # 遍历所有任务
  for task_id in "${TASK_IDS[@]}"; do
    TIMESTAMP=$(date +%H%M%S)
    LOG_FILE="$CONFIG_LOG_DIR/${task_id}_${TIMESTAMP}.log"

    echo "  📝 任务 $task_id -> $LOG_FILE"

    PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python "$PYTHON_SCRIPT" \
      --config "$CONFIG_PATH" \
      --task_id "$task_id" 2>&1 | tee "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
      echo "  ✅ 任务 $task_id 完成"
    else
      echo "  ❌ 任务 $task_id 失败"
    fi
  done

  echo ""
done

echo "========================================================================"
echo "🎉 PostRetrieval 实验全部完成"
echo "📁 日志目录: $LOG_BASE_DIR"
echo "========================================================================"
