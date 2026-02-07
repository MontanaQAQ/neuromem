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

# Print colored messages
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              NeuroMem (sage.neuromem) Quick Start                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
print_info "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
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
print_info "Installing NeuroMem in development mode..."
if pip install -e . > /tmp/neuromem_install.log 2>&1; then
    print_success "NeuroMem installed successfully"
else
    print_error "Installation failed. Check /tmp/neuromem_install.log for details"
    tail -20 /tmp/neuromem_install.log
    exit 1
fi

# Verify installation
print_info "Verifying installation..."
if python3 -c "from sage.neuromem import MemoryManager; print('sage.neuromem import OK')" 2>/dev/null; then
    print_success "Import verification passed"
else
    print_error "Import verification failed"
    print_info "Note: sage.common and isagedb dependencies must be installed separately"
    echo ""
fi

# Install pre-commit hooks (for contributors)
if [[ -f ".pre-commit-config.yaml" ]] && command -v git &> /dev/null; then
    echo ""
    read -p "Install pre-commit hooks for development? (recommended for contributors) (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing pre-commit hooks..."
        if command -v pre-commit &> /dev/null; then
            if pre-commit install > /tmp/precommit_install.log 2>&1; then
                print_success "Pre-commit hooks installed"
            else
                print_warning "Failed to install pre-commit hooks"
            fi
        else
            print_info "Installing pre-commit package..."
            if pip install pre-commit > /dev/null 2>&1; then
                if pre-commit install > /tmp/precommit_install.log 2>&1; then
                    print_success "Pre-commit hooks installed"
                else
                    print_warning "Failed to install pre-commit hooks"
                fi
            else
                print_warning "Failed to install pre-commit package"
                print_info "You can install it later with: pip install pre-commit && pre-commit install"
            fi
        fi
    fi
fi

# Show version
VERSION=$(python3 -c "from sage.neuromem import __version__; print(__version__)" 2>/dev/null || echo "unknown")
print_info "Installed version: $VERSION"

# Optional: Run tests
echo ""
read -p "Run basic tests? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Running tests..."
    if pytest tests/unit/neuromem/test_memory_manager.py -v --tb=short 2>&1 | tail -20; then
        print_success "Tests completed"
    else
        print_warning "Some tests may have failed (check if dependencies are installed)"
    fi
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
    if python3 -c "import $1" 2>/dev/null; then
        print_success "$1 installed"
    else
        print_warning "$1 not installed (optional: $2)"
    fi
}

check_dependency "redis" "for Redis KV backend"
check_dependency "neo4j" "for Neo4j graph backend"
check_dependency "faiss" "for FAISS vector indexing"

echo ""
print_info "To install optional dependencies: pip install 'isage-neuromem[full]'"
echo ""

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete! 🎉                                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
print_success "NeuroMem is ready to use!"
echo ""
print_info "Import path: ${BLUE}from sage.neuromem import MemoryManager${NC}"
print_info "Package: isage-neuromem (v$VERSION)"
echo ""

# Offer to run example
read -p "Run example script? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ -f "examples/memory_os_hybrid_example.py" ]]; then
        print_info "Running example..."
        python3 examples/memory_os_hybrid_example.py 2>&1 | head -50
    else
        print_warning "Example script not found"
    fi
fi

echo ""
print_info "For more information, visit: https://github.com/intellistream/NeuroMem"
echo ""
