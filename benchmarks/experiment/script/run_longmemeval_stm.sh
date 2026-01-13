#!/bin/bash
# 运行 LongMemEval 长轮对话记忆实验 - 短期记忆（STM）批量测试
# 使用方法: bash script/run_longmem_stm.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录 (从 script/ 向上 3 层到 neuromem/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# Python 脚本的相对路径
PYTHON_SCRIPT="$SCRIPT_DIR/../memory_test_pipeline.py"
# 配置文件路径（LongMemEval - STM）
CONFIG_FILE="$SCRIPT_DIR/../config/longmemeval_short_term_memory_pipeline.yaml"

# 可选：LongMemEval 数据文件路径（若 YAML 未配置 data.filepath，可在此指定）
# DATA_FILE="E:/科研/lxy/SAGE/packages/sage-benchmark/src/sage/data/sources/longmemeval/longmemeval_s_cleaned.json"

echo "========================================================================"
echo "LongMemEval 长轮对话记忆实验 - 短期记忆（STM）批量测试"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $PYTHON_SCRIPT"
echo "配置文件: $CONFIG_FILE"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 使用 composed 模式的组 ID 运行（group-1 到 group-10）
TASK_IDS=(
  "group-1"
  "group-2"
  "group-3"
  "group-4"
  "group-5"
  "group-6"
  "group-7"
  "group-8"
  "group-9"
  "group-10"
)

# 创建日志目录结构
DATASET="longmemeval"
MEMORY_NAME="stm"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "总任务数: ${#TASK_IDS[@]}"
echo "日志目录: $LOG_BASE_DIR"
echo ""

# 依次运行所有任务
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))

  # 生成带时间戳的日志目录
  TIMESTAMP=$(date +%H%M%S)
  LOG_DIR="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/terminal.log"

  echo "--------------------------------------------------------------------"
  echo "🚀 开始运行任务 [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "📝 日志目录: $LOG_DIR"
  echo "--------------------------------------------------------------------"
  echo ""

  # 运行实验并将输出重定向到日志文件
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
echo "🎉 所有任务执行完毕！"
echo "📁 所有日志已保存到: $LOG_BASE_DIR"
echo "========================================================================"
