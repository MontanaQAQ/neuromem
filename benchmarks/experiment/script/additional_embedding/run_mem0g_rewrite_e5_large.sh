#!/bin/bash
# 补充实验：Mem0g + Rewrite + e5-large-v2 embedding
# 使用方法: bash benchmarks/experiment/script/additional_embedding/run_mem0g_rewrite_e5_large.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录 (从 script/additional_embedding/ 向上 4 层到 neuromem/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
# Python 脚本的相对路径
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
# 配置文件路径
CONFIG_FILE="$SCRIPT_DIR/../../config/additional_embedding/Mem0g_locomo_rewrite_e5_large.yaml"

# 定义所有任务 ID
TASK_IDS=(
#   "conv-26"
#   "conv-30"
#   "conv-41"
#   "conv-42"
#   "conv-43"
#   "conv-44"
#   "conv-47"
  "conv-48"
  "conv-49"
  "conv-50"
)

# 创建日志目录结构
DATASET="locomo"
MEMORY_NAME="Additional_Mem0g_rewrite_e5_large"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "补充实验: Mem0g + Rewrite + e5-large-v2 Embedding"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $(realpath "$PYTHON_SCRIPT")"
echo "配置文件: $(realpath "$CONFIG_FILE")"
echo "日志目录: $LOG_BASE_DIR"
echo "总任务数: ${#TASK_IDS[@]}"
echo "Embedding模型: intfloat/e5-large-v2 (port 8092)"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 依次运行所有任务
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"

  echo "--------------------------------------------------------------------"
  echo "🚀 开始运行任务 [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "📝 日志文件: $LOG_FILE"
  echo "--------------------------------------------------------------------"

  # 运行实验
  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" PROCESS_LOG_DIR="$LOG_DIR" python "$PYTHON_SCRIPT" \
    --config "$CONFIG_FILE" \
    --task_id "$TASK_ID" \
    2>&1 | tee "$LOG_FILE"

  # 检查执行结果
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ 任务 $TASK_ID 完成，日志已保存到: $LOG_FILE"
  else
    echo "❌ 任务 $TASK_ID 失败，日志已保存到: $LOG_FILE"
    exit 1
  fi

  echo ""
done

echo "========================================================================"
echo "🎉 所有任务执行完毕 - $MEMORY_NAME"
echo "📁 所有日志已保存到: $LOG_BASE_DIR"
echo "========================================================================"
