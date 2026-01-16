#!/bin/bash
# 运行 Mem0g Locomo PreRetrieval 实验 - decompose
# 使用方法: bash script/query_formulation_strategy/run_mem0g_locomo_decompose.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录 (从 script/query_formulation_strategy/ 向上 4 层到 neuromem/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
# Python 脚本的相对路径
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
# 配置文件路径
CONFIG_FILE="$SCRIPT_DIR/../../config/query_formulation_strategy/Mem0g_locomo_decompose_pre_retrieval_pipeline.yaml"

# 定义所有任务 ID
TASK_IDS=(
  "conv-26"
  "conv-30"
  "conv-41"
  "conv-42"
  "conv-43"
  "conv-44"
  "conv-47"
  "conv-48"
  "conv-49"
  "conv-50"
)

# 创建日志目录结构
DATASET="locomo"
MEMORY_NAME="Mem0g-decompose"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "Mem0g Locomo PreRetrieval 实验 - decompose"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $(realpath "$PYTHON_SCRIPT")"
echo "配置文件: $(realpath "$CONFIG_FILE")"
echo "日志目录: $LOG_BASE_DIR"
echo "总任务数: ${#TASK_IDS[@]}"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 依次运行所有任务
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))

  # 生成带时间戳的日志文件名
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"

  echo "--------------------------------------------------------------------"
  echo "🚀 开始运行任务 [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "📝 日志目录: $LOG_DIR"
  echo "--------------------------------------------------------------------"

  # 运行任务并将输出重定向到日志文件（同时显示到终端）
  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ 任务 $TASK_ID 完成，日志已保存到: $LOG_DIR"
  else
    echo "❌ 任务 $TASK_ID 失败，日志已保存到: $LOG_DIR"
    exit 1
  fi

  echo ""
done

echo "========================================================================"
echo "🎉 所有任务执行完毕 - Mem0g-decompose"
echo "📁 所有日志已保存到: $LOG_BASE_DIR"
echo "========================================================================"
