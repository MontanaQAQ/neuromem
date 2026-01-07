#!/usr/bin/env bash
# User-facing example and documentation display for NeuroMem quickstart.

show_quick_example_and_docs() {
    echo ""
    if [[ "$LANG_SETTING" == "zh" ]]; then
        echo "╔══════════════════════════════════════════════════════════════════════╗"
        echo "║                         快速示例                                     ║"
        echo "╚══════════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "在 Python 中尝试:"
    else
        echo "╔══════════════════════════════════════════════════════════════════════╗"
        echo "║                         Quick Example                                ║"
        echo "╚══════════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Try this in Python:"
    fi
    echo ""
    echo -e "${BLUE}from sage.neuromem import MemoryManager${NC}"
    echo ""
    if [[ "$LANG_SETTING" == "zh" ]]; then
        echo -e "${BLUE}# 创建内存管理器${NC}"
    else
        echo -e "${BLUE}# Create memory manager${NC}"
    fi
    echo -e "${BLUE}manager = MemoryManager()${NC}"
    echo ""
    if [[ "$LANG_SETTING" == "zh" ]]; then
        echo -e "${BLUE}# 创建一个集合${NC}"
    else
        echo -e "${BLUE}# Create a collection${NC}"
    fi
    echo -e "${BLUE}config = {${NC}"
    echo -e "${BLUE}    'name': 'my_collection',${NC}"
    echo -e "${BLUE}    'backend_type': 'VDB',${NC}"
    echo -e "${BLUE}    'description': 'My first collection'${NC}"
    echo -e "${BLUE}}${NC}"
    echo -e "${BLUE}collection = manager.create_collection(config)${NC}"
    echo ""

    if [[ "$LANG_SETTING" == "zh" ]]; then
        echo "╔══════════════════════════════════════════════════════════════════════╗"
        echo "║                          文档                                        ║"
        echo "╚══════════════════════════════════════════════════════════════════════╝"
        echo ""
        print_info "README: ./README.md"
        print_info "迁移指南: ./docs/NAMESPACE_MIGRATION_GUIDE.md"
        print_info "贡献指南: ./docs/CONTRIBUTING.md"
        print_info "示例: ./examples/"
    else
        echo "╔══════════════════════════════════════════════════════════════════════╗"
        echo "║                       Documentation                                  ║"
        echo "╚══════════════════════════════════════════════════════════════════════╝"
        echo ""
        print_info "README: ./README.md"
        print_info "Migration Guide: ./docs/NAMESPACE_MIGRATION_GUIDE.md"
        print_info "Contributing: ./docs/CONTRIBUTING.md"
        print_info "Examples: ./examples/"
    fi
    echo ""
}

maybe_run_example_script() {
    if [[ "$LANG_SETTING" == "zh" ]]; then
        read -p "运行示例脚本? (y/N) " -n 1 -r
    else
        read -p "Run example script? (y/N) " -n 1 -r
    fi
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ -f "examples/memory_os_hybrid_example.py" ]]; then
            if [[ "$LANG_SETTING" == "zh" ]]; then
                print_info "正在运行示例..."
            else
                print_info "Running example..."
            fi
            echo "=== Example Execution Started at $(date) ===" >> "$LOG_FILE"
            $PYTHON_CMD examples/memory_os_hybrid_example.py 2>&1 | tee -a "$LOG_FILE" | head -50
            echo "=== Example Execution Completed at $(date) ===" >> "$LOG_FILE"
        else
            if [[ "$LANG_SETTING" == "zh" ]]; then
                print_warning "示例脚本未找到"
            else
                print_warning "Example script not found"
            fi
        fi
    fi
}

show_final_summary() {
    echo ""
    if [[ "$LANG_SETTING" == "zh" ]]; then
        echo "╔══════════════════════════════════════════════════════════════════════╗"
        echo "║                          安装完成！                                  ║"
        echo "╚══════════════════════════════════════════════════════════════════════╝"
        echo ""
        print_success "NeuroMem 已准备就绪!"
        echo ""
        print_info "导入路径: ${BLUE}from sage.neuromem import MemoryManager${NC}"
        print_info "包名: isage-neuromem (v$VERSION)"
        print_info "安装日志保存到: $LOG_FILE"
        echo ""
        print_info "更多信息请访问: https://github.com/intellistream/NeuroMem"
    else
        echo "╔══════════════════════════════════════════════════════════════════════╗"
        echo "║                        Setup Complete!                               ║"
        echo "╚══════════════════════════════════════════════════════════════════════╝"
        echo ""
        print_success "NeuroMem is ready to use!"
        echo ""
        print_info "Import path: ${BLUE}from sage.neuromem import MemoryManager${NC}"
        print_info "Package: isage-neuromem (v$VERSION)"
        print_info "Installation log saved to: $LOG_FILE"
        echo ""
        print_info "For more information, visit: https://github.com/intellistream/NeuroMem"
    fi
    echo ""
    echo "=== Installation Script Completed at $(date) ===" >> "$LOG_FILE"
    echo "Full installation log: $LOG_FILE" >> "$LOG_FILE"
}
