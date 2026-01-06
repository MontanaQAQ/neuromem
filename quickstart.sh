#!/bin/bash
# NeuroMem Quick Start Script
# Helps users quickly set up and test NeuroMem (sage.neuromem)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Setup logging
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$HOME/.sage/installation/neuromem"
LOG_FILE="$LOG_DIR/install_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Initialize log file
echo "NeuroMem Installation Log - $TIMESTAMP" > "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Logging function - outputs to both console and log file
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Print colored messages (with logging)
print_success() {
    echo -e "${GREEN}✓${NC} $1"
    echo "[SUCCESS] $1" >> "$LOG_FILE"
}
print_error() {
    echo -e "${RED}✗${NC} $1"
    echo "[ERROR] $1" >> "$LOG_FILE"
}
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
    echo "[INFO] $1" >> "$LOG_FILE"
}
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    echo "[WARNING] $1" >> "$LOG_FILE"
}

# Detect Python command (prefer python over python3 for conda environments)
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    print_error "Python not found. Please install Python 3.10+"
    exit 1
fi

log ""
log "╔══════════════════════════════════════════════════════════════════════╗"
log "║              NeuroMem (sage.neuromem) Quick Start                    ║"
log "╚══════════════════════════════════════════════════════════════════════╝"
log ""

print_info "Installation log: $LOG_FILE"
log ""

# Check Python version
print_info "Checking Python version..."
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    print_success "Python $PYTHON_VERSION detected (>= 3.10 required)"
else
    print_error "Python 3.10+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

# Check if in virtual environment
if [[ -z "$VIRTUAL_ENV" ]] && [[ -z "$CONDA_DEFAULT_ENV" ]]; then
    print_warning "Not in a virtual environment. Recommend creating one:"
    echo "           python3 -m venv venv && source venv/bin/activate"
    echo ""
    read -p "Continue without virtual environment? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Exiting. Please activate a virtual environment first."
        exit 0
    fi
fi

# Install in development mode
print_info "Installing NeuroMem in development mode (with benchmark dependencies)..."
echo "=== Installation Started at $(date) ===" >> "$LOG_FILE"
if $PYTHON_CMD -m pip install -e .[benchmark] >> "$LOG_FILE" 2>&1; then
    print_success "NeuroMem installed successfully"
    echo "=== Installation Completed at $(date) ===" >> "$LOG_FILE"
else
    print_error "Installation failed. Check $LOG_FILE for details"
    echo "=== Installation Failed at $(date) ===" >> "$LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi

# Verify installation
print_info "Verifying installation..."
echo "=== Verification Started at $(date) ===" >> "$LOG_FILE"
VERIFY_OUTPUT=$($PYTHON_CMD -c "from sage.neuromem import MemoryManager; print('sage.neuromem import OK')" 2>&1)
echo "$VERIFY_OUTPUT" >> "$LOG_FILE"
if echo "$VERIFY_OUTPUT" | grep -q "sage.neuromem import OK"; then
    print_success "Import verification passed"
    echo "=== Verification Passed at $(date) ===" >> "$LOG_FILE"
else
    print_error "Import verification failed"
    print_info "Trying to diagnose the issue..."
    echo "=== Verification Failed at $(date) ===" >> "$LOG_FILE"
    $PYTHON_CMD -c "from sage.neuromem import MemoryManager" 2>&1 | tee -a "$LOG_FILE" || true
    echo ""
fi

# Install pre-commit hooks (for contributors)
if [[ -f ".pre-commit-config.yaml" ]] && command -v git &> /dev/null; then
    echo ""
    read -p "Install pre-commit hooks for development? (recommended for contributors) (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing pre-commit hooks..."
        echo "=== Pre-commit Installation Started at $(date) ===" >> "$LOG_FILE"
        if command -v pre-commit &> /dev/null; then
            if pre-commit install >> "$LOG_FILE" 2>&1; then
                print_success "Pre-commit hooks installed"
            else
                print_warning "Failed to install pre-commit hooks"
            fi
        else
            print_info "Installing pre-commit package..."
            if pip install pre-commit >> "$LOG_FILE" 2>&1; then
                if pre-commit install >> "$LOG_FILE" 2>&1; then
                    print_success "Pre-commit hooks installed"
                else
                    print_warning "Failed to install pre-commit hooks"
                fi
            else
                print_warning "Failed to install pre-commit package"
                print_info "You can install it later with: pip install pre-commit && pre-commit install"
            fi
        fi
        echo "=== Pre-commit Installation Completed at $(date) ===" >> "$LOG_FILE"
    fi
fi

# Show version
VERSION=$($PYTHON_CMD -c "from sage.neuromem import __version__; print(__version__)" 2>/dev/null || echo "unknown")
print_info "Installed version: $VERSION"
echo "Installed version: $VERSION" >> "$LOG_FILE"

# Optional: Run tests
echo ""
read -p "Run basic tests? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Running tests..."
    echo "=== Tests Started at $(date) ===" >> "$LOG_FILE"
    if pytest tests/unit/neuromem/test_memory_manager.py -v --tb=short 2>&1 | tee -a "$LOG_FILE" | tail -20; then
        print_success "Tests completed"
    else
        print_warning "Some tests may have failed (check if dependencies are installed)"
    fi
    echo "=== Tests Completed at $(date) ===" >> "$LOG_FILE"
fi

# Show quick example
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                         Quick Example                                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Try this in Python:"
echo ""
echo -e "${BLUE}from sage.neuromem import MemoryManager${NC}"
echo ""
echo -e "${BLUE}# Create memory manager${NC}"
echo -e "${BLUE}manager = MemoryManager()${NC}"
echo ""
echo -e "${BLUE}# Create a collection${NC}"
echo -e "${BLUE}config = {${NC}"
echo -e "${BLUE}    'name': 'my_collection',${NC}"
echo -e "${BLUE}    'backend_type': 'VDB',${NC}"
echo -e "${BLUE}    'description': 'My first collection'${NC}"
echo -e "${BLUE}}${NC}"
echo -e "${BLUE}collection = manager.create_collection(config)${NC}"
echo ""

# Show documentation links
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                       Documentation                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
print_info "README: ./README.md"
print_info "Migration Guide: ./docs/NAMESPACE_MIGRATION_GUIDE.md"
print_info "Contributing: ./docs/CONTRIBUTING.md"
print_info "Examples: ./examples/"
echo ""

# Check for optional dependencies
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                   Optional Dependencies                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

check_dependency() {
    if $PYTHON_CMD -c "import $1" 2>/dev/null; then
        print_success "$1 installed"
        echo "[DEPENDENCY] $1 - installed" >> "$LOG_FILE"
    else
        print_warning "$1 not installed (optional: $2)"
        echo "[DEPENDENCY] $1 - NOT installed ($2)" >> "$LOG_FILE"
    fi
}

echo "=== Dependency Check Started at $(date) ===" >> "$LOG_FILE"
check_dependency "redis" "for Redis KV backend"
check_dependency "neo4j" "for Neo4j graph backend"
check_dependency "faiss" "for FAISS vector indexing"
check_dependency "bm25s" "for BM25s text indexing"
check_dependency "datasketch" "for LSH indexing"
check_dependency "pandas" "for benchmark data analysis"
check_dependency "matplotlib" "for benchmark visualization"
echo "=== Dependency Check Completed at $(date) ===" >> "$LOG_FILE"

echo ""
print_info "All dependencies installed (benchmark mode)"
echo ""

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete! 🎉                                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
print_success "NeuroMem is ready to use!"
echo ""
print_info "Import path: ${BLUE}from sage.neuromem import MemoryManager${NC}"
print_info "Package: isage-neuromem (v$VERSION)"
print_info "Installation log saved to: $LOG_FILE"
echo ""

# Offer to run example
read -p "Run example script? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ -f "examples/memory_os_hybrid_example.py" ]]; then
        print_info "Running example..."
        echo "=== Example Execution Started at $(date) ===" >> "$LOG_FILE"
        $PYTHON_CMD examples/memory_os_hybrid_example.py 2>&1 | tee -a "$LOG_FILE" | head -50
        echo "=== Example Execution Completed at $(date) ===" >> "$LOG_FILE"
    else
        print_warning "Example script not found"
    fi
fi

echo ""
print_info "For more information, visit: https://github.com/intellistream/NeuroMem"
echo ""
echo "=== Installation Script Completed at $(date) ===" >> "$LOG_FILE"
echo "Full installation log: $LOG_FILE" >> "$LOG_FILE"
