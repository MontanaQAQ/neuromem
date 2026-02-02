#!/bin/bash
# 补充实验：Mem0g + Augment + Llama-3-8B
# 使用方法: bash benchmarks/experiment/script/additional_model_llama/run_mem0g_augment_llama.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
# Python 脚本的相对路径
PYTHON_SCRIPT="$PROJECT_ROOT/benchmarks/experiment/memory_test_pipeline.py"
# 配置文件路径
CONFIG_FILE="$PROJECT_ROOT/benchmarks/experiment/config/additional_experiments_ds_llama/llama_context_integration_mechanism/Mem0g_locomo_augment_post_retrieval_pipeline.yaml"

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
MEMORY_NAME="PostRetrieval_Mem0g_augment_Llama"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "补充实验: Mem0g + Augment + Llama-3-8B"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $PYTHON_SCRIPT"
echo "配置文件: $CONFIG_FILE"
echo "日志目录: $LOG_BASE_DIR"
echo "总任务数: ${#TASK_IDS[@]}"
echo "LLM模型: meta-llama/Meta-Llama-3-8B-Instruct (sage2:8001)"
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
