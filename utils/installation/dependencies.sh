#!/usr/bin/env bash
# Optional dependency checks for NeuroMem.

check_dependency() {
    local module=$1
    local description=$2
    local description_zh=$3

    if $PYTHON_CMD -c "import $module" 2>/dev/null; then
        if [[ "$LANG_SETTING" == "zh" ]]; then
            print_success "$module 已安装"
        else
            print_success "$module installed"
        fi
        echo "[DEPENDENCY] $module - installed" >> "$LOG_FILE"
    else
        if [[ "$LANG_SETTING" == "zh" ]]; then
            print_warning "$module 未安装 (可选: ${description_zh:-$description})"
        else
            print_warning "$module not installed (optional: $description)"
        fi
        echo "[DEPENDENCY] $module - NOT installed ($description)" >> "$LOG_FILE"
    fi
}

check_optional_dependencies() {
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    if [[ "$LANG_SETTING" == "zh" ]]; then
        echo "║                      可选依赖                                        ║"
    else
        echo "║                   Optional Dependencies                              ║"
    fi
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""

    echo "=== Dependency Check Started at $(date) ===" >> "$LOG_FILE"
    check_dependency "redis" "for Redis KV backend" "用于 Redis KV 后端"
    check_dependency "neo4j" "for Neo4j graph backend" "用于 Neo4j 图后端"
    check_dependency "faiss" "for FAISS vector indexing" "用于 FAISS 向量索引"
    check_dependency "bm25s" "for BM25s text indexing" "用于 BM25s 文本索引"
    check_dependency "datasketch" "for LSH indexing" "用于 LSH 索引"
    check_dependency "pandas" "for benchmark data analysis" "用于 benchmark 数据分析"
    check_dependency "matplotlib" "for benchmark visualization" "用于 benchmark 可视化"
    echo "=== Dependency Check Completed at $(date) ===" >> "$LOG_FILE"

    echo ""
    if [[ "$LANG_SETTING" == "zh" ]]; then
        print_info "所有依赖已安装 (benchmark 模式)"
    else
        print_info "All dependencies installed (benchmark mode)"
    fi
    echo ""
}
