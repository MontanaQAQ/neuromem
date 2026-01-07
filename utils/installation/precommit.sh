#!/usr/bin/env bash
# Optional pre-commit hook installation for contributors.

maybe_install_precommit() {
    if [[ -f ".pre-commit-config.yaml" && $(command -v git >/dev/null 2>&1; echo $?) -eq 0 ]]; then
        echo ""
        if [[ "$LANG_SETTING" == "zh" ]]; then
            echo "Pre-commit 可以在 git commit 前自动检查代码格式、语法错误等问题"
            echo "（适合需要提交代码的开发者，普通使用者可跳过）"
            echo ""
            read -p "是否安装 pre-commit 钩子? (y/N) " -n 1 -r
        else
            echo "Pre-commit automatically checks code format, syntax errors, etc. before git commit"
            echo "(Useful for contributors who will submit code, optional for regular users)"
            echo ""
            read -p "Install pre-commit hooks? (y/N) " -n 1 -r
        fi
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [[ "$LANG_SETTING" == "zh" ]]; then
                print_info "正在安装 pre-commit 钩子..."
            else
                print_info "Installing pre-commit hooks..."
            fi
            echo "=== Pre-commit Installation Started at $(date) ===" >> "$LOG_FILE"
            if command -v pre-commit &> /dev/null; then
                if pre-commit install >> "$LOG_FILE" 2>&1; then
                    if [[ "$LANG_SETTING" == "zh" ]]; then
                        print_success "Pre-commit 钩子安装成功"
                    else
                        print_success "Pre-commit hooks installed"
                    fi
                else
                    if [[ "$LANG_SETTING" == "zh" ]]; then
                        print_warning "安装 pre-commit 钩子失败"
                    else
                        print_warning "Failed to install pre-commit hooks"
                    fi
                fi
            else
                if [[ "$LANG_SETTING" == "zh" ]]; then
                    print_info "正在安装 pre-commit 包..."
                else
                    print_info "Installing pre-commit package..."
                fi
                if $PYTHON_CMD -m pip install pre-commit >> "$LOG_FILE" 2>&1; then
                    if pre-commit install >> "$LOG_FILE" 2>&1; then
                        if [[ "$LANG_SETTING" == "zh" ]]; then
                            print_success "Pre-commit 钩子安装成功"
                        else
                            print_success "Pre-commit hooks installed"
                        fi
                    else
                        if [[ "$LANG_SETTING" == "zh" ]]; then
                            print_warning "安装 pre-commit 钩子失败"
                        else
                            print_warning "Failed to install pre-commit hooks"
                        fi
                    fi
                else
                    if [[ "$LANG_SETTING" == "zh" ]]; then
                        print_warning "安装 pre-commit 包失败"
                        print_info "您可以稍后安装: pip install pre-commit && pre-commit install"
                    else
                        print_warning "Failed to install pre-commit package"
                        print_info "You can install it later with: pip install pre-commit && pre-commit install"
                    fi
                fi
            fi
            echo "=== Pre-commit Installation Completed at $(date) ===" >> "$LOG_FILE"
        fi
    fi
}
