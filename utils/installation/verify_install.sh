#!/usr/bin/env bash
# Verification helpers for NeuroMem installation.

verify_neuromem_install() {
    if [[ "$LANG_SETTING" == "zh" ]]; then
        print_info "验证安装..."
    else
        print_info "Verifying installation..."
    fi
    echo "=== Verification Started at $(date) ===" >> "$LOG_FILE"
    local verify_output
    verify_output=$($PYTHON_CMD -c "from sage.neuromem import MemoryManager; print('sage.neuromem import OK')" 2>&1)
    echo "$verify_output" >> "$LOG_FILE"
    if echo "$verify_output" | grep -q "sage.neuromem import OK"; then
        if [[ "$LANG_SETTING" == "zh" ]]; then
            print_success "导入验证通过"
        else
            print_success "Import verification passed"
        fi
        echo "=== Verification Passed at $(date) ===" >> "$LOG_FILE"
    else
        if [[ "$LANG_SETTING" == "zh" ]]; then
            print_error "导入验证失败"
            print_info "尝试诊断问题..."
        else
            print_error "Import verification failed"
            print_info "Trying to diagnose the issue..."
        fi
        echo "=== Verification Failed at $(date) ===" >> "$LOG_FILE"
        $PYTHON_CMD -c "from sage.neuromem import MemoryManager" 2>&1 | tee -a "$LOG_FILE" || true
        echo ""
    fi
}

show_installed_version() {
    VERSION=$($PYTHON_CMD -c "from sage.neuromem import __version__; print(__version__)" 2>/dev/null || echo "unknown")
    export VERSION
    if [[ "$LANG_SETTING" == "zh" ]]; then
        print_info "已安装版本: $VERSION"
    else
        print_info "Installed version: $VERSION"
    fi
    echo "Installed version: $VERSION" >> "$LOG_FILE"
}
