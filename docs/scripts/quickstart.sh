#!/bin/bash
# 🚀 NeuroMem 快速安装脚本
# Brain-inspired memory system for SAGE framework

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color
DIM='\033[2m'
BOLD='\033[1m'

# Get script directory
NEUROMEM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
DEV_MODE=false
AUTO_YES=false
PYTHON_CMD="python"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        --yes|-y)
            AUTO_YES=true
            shift
            ;;
        --help|-h)
            echo "NeuroMem Installation Script"
            echo ""
            echo "Usage: ./quickstart.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev          Install in development mode (editable install)"
            echo "  --yes, -y      Auto-confirm all prompts"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./quickstart.sh --dev --yes          # Development install"
            echo "  ./quickstart.sh                      # Production install"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Helper functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
}

step() {
    echo -e "\n${BOLD}${BLUE}▶${NC} ${BOLD}$1${NC}"
}

# Check Python version
check_python() {
    step "Checking Python environment"

    if ! command -v python &> /dev/null; then
        if command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        else
            error "Python not found. Please install Python 3.10+"
            exit 1
        fi
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
        error "Python 3.10+ required (found $PYTHON_VERSION)"
        exit 1
    fi

    success "Python $PYTHON_VERSION detected"
}

# Check dependencies
check_dependencies() {
    step "Checking system dependencies"

    # Check for required packages
    MISSING_DEPS=()

    if ! command -v git &> /dev/null; then
        MISSING_DEPS+=("git")
    fi

    if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
        error "Missing dependencies: ${MISSING_DEPS[*]}"
        echo ""
        echo "Install them with:"
        echo "  Ubuntu/Debian: sudo apt-get install ${MISSING_DEPS[*]}"
        echo "  macOS: brew install ${MISSING_DEPS[*]}"
        exit 1
    fi

    success "All system dependencies satisfied"
}

# Install Python dependencies
install_dependencies() {
    step "Installing Python dependencies"

    # Check if isage-common is installed
    if ! $PYTHON_CMD -c "import sage.common" &> /dev/null; then
        warn "isage-common not found. Installing..."
        $PYTHON_CMD -m pip install isage-common --upgrade
    fi

    # Check if isagevdb is installed
    if ! $PYTHON_CMD -c "import sagevdb" &> /dev/null; then
        warn "isagevdb not found. Installing..."
        $PYTHON_CMD -m pip install isagevdb --upgrade
    fi

    success "Dependencies installed"
}

# Install NeuroMem
install_neuromem() {
    step "Installing NeuroMem"

    cd "$NEUROMEM_ROOT"

    if [ "$DEV_MODE" = true ]; then
        info "Installing in development mode (editable)"
        $PYTHON_CMD -m pip install -e . --no-deps
    else
        info "Installing NeuroMem"
        $PYTHON_CMD -m pip install .
    fi

    success "NeuroMem installed successfully"
}

# Setup pre-commit hooks (dev mode only)
setup_hooks() {
    if [ "$DEV_MODE" = true ]; then
        step "Setting up pre-commit hooks"

        if ! command -v pre-commit &> /dev/null; then
            info "Installing pre-commit"
            $PYTHON_CMD -m pip install pre-commit
        fi

        info "Installing Git hooks"
        pre-commit install

        success "Pre-commit hooks installed"
    fi
}

# Run tests
run_tests() {
    step "Running tests"

    if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
        warn "pytest not found. Installing..."
        $PYTHON_CMD -m pip install pytest pytest-cov pytest-mock
    fi

    info "Running unit tests (quick check)..."
    if $PYTHON_CMD -m pytest tests/unit/ -x -q --tb=short; then
        success "Tests passed"
    else
        warn "Some tests failed. Review the output above."
        warn "This is normal for a fresh install. Run 'pytest tests/unit/ -v' for details."
    fi
}

# Verify installation
verify_installation() {
    step "Verifying installation"

    if $PYTHON_CMD -c "from neuromem import MemoryManager; print('NeuroMem version:', __import__('neuromem').__version__)" 2>/dev/null; then
        success "NeuroMem installed and importable"
    else
        error "Failed to import NeuroMem"
        exit 1
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${GREEN}  NeuroMem Installation Complete!${NC}"
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BOLD}Quick Start:${NC}"
    echo ""
    echo -e "  ${DIM}# Import NeuroMem${NC}"
    echo -e "  from neuromem import MemoryManager"
    echo -e "  manager = MemoryManager()"
    echo ""

    if [ "$DEV_MODE" = true ]; then
        echo -e "${BOLD}Development Commands:${NC}"
        echo ""
        echo -e "  ${DIM}# Run tests${NC}"
        echo -e "  pytest tests/unit/ -v"
        echo ""
        echo -e "  ${DIM}# Run with coverage${NC}"
        echo -e "  pytest tests/unit/ --cov=neuromem --cov-report=html"
        echo ""
        echo -e "  ${DIM}# Format code${NC}"
        echo -e "  pre-commit run --all-files"
        echo ""
    fi

    echo -e "${BOLD}Documentation:${NC}"
    echo -e "  ${DIM}# Project README${NC}"
    echo -e "  cat README.md"
    echo ""
    echo -e "  ${DIM}# Copilot instructions${NC}"
    echo -e "  cat .github/copilot-instructions.md"
    echo ""
    echo -e "${DIM}For more information, visit: https://github.com/intellistream/NeuroMem${NC}"
    echo ""
}

# Main installation flow
main() {
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  NeuroMem Installation${NC}"
    echo -e "${BOLD}${BLUE}  Brain-inspired memory system for SAGE${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ "$DEV_MODE" = true ]; then
        info "Mode: ${BOLD}Development${NC} (editable install + pre-commit hooks)"
    else
        info "Mode: ${BOLD}Production${NC} (standard install)"
        info "Tip: Use ${DIM}--dev${NC} for development mode"
    fi

    echo ""

    # Confirm if not auto-yes
    if [ "$AUTO_YES" = false ]; then
        read -p "Continue with installation? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Installation cancelled"
            exit 0
        fi
    fi

    # Installation steps
    check_python
    check_dependencies
    install_dependencies
    install_neuromem

    if [ "$DEV_MODE" = true ]; then
        setup_hooks
    fi

    verify_installation

    # Optional: run tests
    if [ "$AUTO_YES" = false ] && [ "$DEV_MODE" = true ]; then
        echo ""
        read -p "Run unit tests? (recommended) (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_tests
        fi
    elif [ "$DEV_MODE" = true ]; then
        run_tests
    fi

    print_summary
}

# Run main function
main
