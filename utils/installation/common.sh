#!/usr/bin/env bash
# Common functions and setup for NeuroMem quickstart and installation scripts.

set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Language setting (default: en)
LANG_SETTING="en"

# Language selection
select_language() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║              NeuroMem (sage.neuromem) Quick Start                    ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Please select your preferred language / 请选择您的语言:"
    echo ""
    echo "  1) English"
    echo "  2) 中文"
    echo ""
    read -p "Enter your choice (1 or 2) / 请输入选项 (1 或 2) [Default: 1]: " -n 1 -r lang_choice
    echo ""
    echo ""

    case $lang_choice in
        2)
            LANG_SETTING="zh"
            ;;
        1|"")
            LANG_SETTING="en"
            ;;
        *)
            echo "Invalid choice, using English / 无效选项，使用英文"
            LANG_SETTING="en"
            ;;
    esac

    export LANG_SETTING
}

# Get localized message
get_msg() {
    local key="$1"

    # English messages
    declare -A MSG_EN
    MSG_EN["installation_log"]="Installation log"
    MSG_EN["checking_conda"]="Checking conda environment..."
    MSG_EN["conda_detected"]="Conda environment detected: %s"
    MSG_EN["conda_python_version"]="Python %s (>= 3.11 required)"
    MSG_EN["conda_not_found"]="Conda environment not detected!"
    MSG_EN["conda_requirement"]="NeuroMem requires a conda environment with Python 3.11+"
    MSG_EN["conda_install_guide"]="Please install conda and create an environment:"
    MSG_EN["conda_create_cmd"]="  conda create -n sage-mem python=3.11 -y"
    MSG_EN["conda_activate_cmd"]="  conda activate sage-mem"
    MSG_EN["python_version_error"]="Python version error! Required: Python 3.11+, Current: %s"
    MSG_EN["python_version_guide"]="Please create a conda environment with Python 3.11:"

    # Chinese messages
    declare -A MSG_ZH
    MSG_ZH["installation_log"]="安装日志"
    MSG_ZH["checking_conda"]="检查 conda 环境..."
    MSG_ZH["conda_detected"]="检测到 Conda 环境: %s"
    MSG_ZH["conda_python_version"]="Python %s (需要 >= 3.11)"
    MSG_ZH["conda_not_found"]="未检测到 Conda 环境！"
    MSG_ZH["conda_requirement"]="NeuroMem 需要一个 Python 3.11+ 的 conda 环境"
    MSG_ZH["conda_install_guide"]="请安装 conda 并创建环境："
    MSG_ZH["conda_create_cmd"]="  conda create -n sage-mem python=3.11 -y"
    MSG_ZH["conda_activate_cmd"]="  conda activate sage-mem"
    MSG_ZH["python_version_error"]="Python 版本错误！需要: Python 3.11+，当前: %s"
    MSG_ZH["python_version_guide"]="请创建一个 Python 3.11 的 conda 环境："

    if [[ "$LANG_SETTING" == "zh" ]]; then
        echo "${MSG_ZH[$key]}"
    else
        echo "${MSG_EN[$key]}"
    fi
}

# Initialize logging (sets LOG_DIR and LOG_FILE)
init_logging() {
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    # Use project directory instead of home directory
    local project_root
    project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    LOG_DIR="$project_root/.sage/installation/neuromem"
    LOG_FILE="$LOG_DIR/install_${timestamp}.log"

    mkdir -p "$LOG_DIR"

    {
        echo "NeuroMem Installation Log - $timestamp"
        echo "========================================"
        echo ""
    } > "$LOG_FILE"
}

# Logging helpers - output to console and log file when available
log() {
    if [[ -n "$LOG_FILE" ]]; then
        echo -e "$1" | tee -a "$LOG_FILE"
    else
        echo -e "$1"
    fi
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    if [[ -n "$LOG_FILE" ]]; then
        echo "[SUCCESS] $1" >> "$LOG_FILE"
    fi
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    if [[ -n "$LOG_FILE" ]]; then
        echo "[ERROR] $1" >> "$LOG_FILE"
    fi
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
    if [[ -n "$LOG_FILE" ]]; then
        echo "[INFO] $1" >> "$LOG_FILE"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    if [[ -n "$LOG_FILE" ]]; then
        echo "[WARNING] $1" >> "$LOG_FILE"
    fi
}

print_main_banner() {
    # Banner is now shown in select_language, skip duplicate
    if [[ "$LANG_SETTING" == "zh" ]]; then
        log ""
        log "开始安装..."
        log ""
    else
        log ""
        log "Starting installation..."
        log ""
    fi
}

# Check if running in conda environment (required)
check_conda_environment() {
    print_info "$(get_msg 'checking_conda')"

    # Check if in conda environment
    if [[ -z "$CONDA_DEFAULT_ENV" ]]; then
        print_error "$(get_msg 'conda_not_found')"
        echo ""
        print_error "$(get_msg 'conda_requirement')"
        echo ""
        print_info "$(get_msg 'conda_install_guide')"
        echo ""
        echo "$(get_msg 'conda_create_cmd')"
        echo "$(get_msg 'conda_activate_cmd')"
        echo ""
        exit 1
    fi

    # Conda environment detected
    printf -v msg "$(get_msg 'conda_detected')" "$CONDA_DEFAULT_ENV"
    print_success "$msg"

    # Use python command in conda environment
    PYTHON_CMD="python"

    # Check Python version (require 3.11+)
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')

    if $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
        printf -v msg "$(get_msg 'conda_python_version')" "$PYTHON_VERSION"
        print_success "$msg"
    else
        printf -v msg "$(get_msg 'python_version_error')" "$PYTHON_VERSION"
        print_error "$msg"
        echo ""
        print_info "$(get_msg 'python_version_guide')"
        echo ""
        echo "$(get_msg 'conda_create_cmd')"
        echo "$(get_msg 'conda_activate_cmd')"
        echo ""
        exit 1
    fi
}
