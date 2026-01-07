#!/usr/bin/env bash
# Development-mode installation for NeuroMem.

install_neuromem_dev() {
    if [[ "$LANG_SETTING" == "zh" ]]; then
        print_info "正在安装 NeuroMem 开发模式 (包含 benchmark 依赖)..."
    else
        print_info "Installing NeuroMem in development mode (with benchmark dependencies)..."
    fi

    echo "=== Installation Started at $(date) ===" >> "$LOG_FILE"

    # Run pip install in background
    $PYTHON_CMD -m pip install -e .[benchmark] >> "$LOG_FILE" 2>&1 &
    local pip_pid=$!

    # Simple spinner with text
    local spin='-\|/'
    local i=0
    while kill -0 $pip_pid 2>/dev/null; do
        i=$(( (i+1) %4 ))
        if [[ "$LANG_SETTING" == "zh" ]]; then
            printf "\r  ${spin:$i:1} 安装中...  "
        else
            printf "\r  ${spin:$i:1} Installing...  "
        fi
        sleep 0.3
    done

    # Wait for pip to finish and get exit code
    wait $pip_pid
    local exit_code=$?

    printf "\r"  # Clear spinner line
    echo ""     # New line

    if [ $exit_code -eq 0 ]; then
        if [[ "$LANG_SETTING" == "zh" ]]; then
            print_success "NeuroMem 安装成功"
        else
            print_success "NeuroMem installed successfully"
        fi
        echo "=== Installation Completed at $(date) ===" >> "$LOG_FILE"
    else
        if [[ "$LANG_SETTING" == "zh" ]]; then
            print_error "安装失败。查看详情: $LOG_FILE"
        else
            print_error "Installation failed. Check $LOG_FILE for details"
        fi
        echo "=== Installation Failed at $(date) ===" >> "$LOG_FILE"
        if [[ "$LANG_SETTING" == "zh" ]]; then
            print_info "检查日志文件以获取详细信息: $LOG_FILE"
        else
            print_info "Check log file for details: $LOG_FILE"
        fi
        exit 1
    fi
}
