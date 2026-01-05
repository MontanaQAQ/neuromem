# Neuromem CI/CD Configuration

This document describes the CI/CD setup for the neuromem repository.

## Overview

Neuromem is a submodule of the SAGE project but also maintains its own CI/CD pipeline for:
- Code quality checks
- Build validation
- Pre-commit hooks for local development

**Note**: Comprehensive tests are run in the main SAGE repository where neuromem is integrated.

## Tool Versions

To ensure consistency between local development, CI/CD, and SAGE main repository:

- **Ruff**: `0.14.2` (pinned to match SAGE main repo)
- **Python**: `3.11` (default), supports `3.8+`
- **Pre-commit hooks**: `v5.0.0`

**Version Consistency**:
- `.pre-commit-config.yaml`: Uses `ruff-pre-commit@v0.14.2`
- `.github/workflows/test.yml`: Installs `ruff==0.14.2`
- `setup.py`: Requires `ruff==0.14.2` in dev dependencies
- **SAGE main repo**: Also uses `ruff@v0.14.2`

This ensures that:
- `pre-commit run --all-files` produces the same results as CI/CD checks
- neuromem code quality standards align with SAGE main repository
- No version conflicts when developing within SAGE

## GitHub Actions CI/CD

### Workflow: `.github/workflows/test.yml`

Runs automatically on:
- Push to `main-dev` or `feat/*` branches
- Pull requests to `main-dev`
- Manual trigger via workflow_dispatch

#### Jobs

1. **lint** (10 min timeout)
   - Runs Ruff linter and formatter checks
   - Ensures code style consistency
   - Uses Python 3.11

2. **validate** (10 min timeout)
   - Validates `pyproject.toml` structure
   - Checks Python syntax across all files
   - Lightweight validation without full dependency install

3. **build** (15 min timeout)
   - Builds the Python package
   - Validates package structure with `twine check`
   - Ensures package can be distributed

### Required Secrets

No secrets required for basic CI/CD (lint, validate, build).

## Pre-commit Hooks

### Installation

From the neuromem repository root:

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# Test on all files
pre-commit run --all-files
```

### Hooks Included

1. **File Checks** (from pre-commit-hooks)
   - Trailing whitespace removal
   - End-of-file fixer
   - YAML/JSON/TOML validation
   - Large file detection (>500KB)
   - Merge conflict detection
   - Line ending normalization (LF)
   - Private key detection

2. **Ruff** (Python linter and formatter)
   - Auto-fixes import sorting
   - Enforces code style (replaces black, isort, flake8)
   - Runs on every commit

3. **Python Syntax Check**
   - Lightweight syntax validation
   - No external dependencies required

### Usage

```bash
# Hooks run automatically on commit
git commit -m "Your message"

# Run manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Skip hooks (not recommended)
git commit --no-verify

# Update hook versions
pre-commit autoupdate
```

## Local Development Workflow

### Recommended Setup

```bash
# 1. Clone repository
git clone https://github.com/intellistream/neuromem.git
cd neuromem

# 2. Install pre-commit
pip install pre-commit
pre-commit install

# 3. Make changes
# ... edit files ...

# 4. Pre-commit runs automatically
git add .
git commit -m "feat: add new feature"

# 5. Push (CI runs automatically)
git push origin your-branch
```

### Integration Testing

Neuromem is tested comprehensively as part of SAGE:

```bash
# In SAGE repository
cd /path/to/SAGE

# Run neuromem-specific tests
pytest packages/sage-middleware/tests/components/sage_mem/ -v

# Run all sage-middleware tests
pytest packages/sage-middleware/tests/ -v
```

## Code Quality Standards

### Ruff Configuration

- **Line length**: 100 characters
- **Target**: Python 3.10+
- **Rules**: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, bugbear, comprehensions, simplify
- **Ignored**: E501 (line length), B008 (function calls in defaults)

### File Structure

```
neuromem/
├── .github/
│   └── workflows/
│       └── test.yml          # CI/CD workflow
├── .pre-commit-config.yaml   # Pre-commit hooks
├── pyproject.toml            # Tool configuration
├── CI_CD_README.md           # This file
├── README.md                 # Main documentation
├── SUBMODULE.md              # Submodule usage guide
├── memory_collection/        # Core modules
├── storage_engine/
├── search_engine/
├── utils/
└── examples/                 # Example scripts
```

## Troubleshooting

### Pre-commit Issues

```bash
# Clear cache
pre-commit clean

# Reinstall hooks
pre-commit uninstall
pre-commit install

# Update to latest versions
pre-commit autoupdate
```

### CI Failures

1. **Lint failures**: Run `pre-commit run --all-files` locally first
2. **Build failures**: Check `pyproject.toml` and `setup.py`
3. **Validation failures**: Ensure all Python files have valid syntax

### Common Errors

**Import errors in CI**:
- Neuromem uses relative imports (e.g., `from .storage_engine import ...`)
- Must be installed as a package or have proper PYTHONPATH
- CI validates syntax only, full import testing happens in SAGE

**Ruff formatting conflicts**:
```bash
# Auto-fix most issues
ruff check --fix .
ruff format .
```

## Maintenance

### Updating Dependencies

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Update GitHub Actions
# Manually update versions in .github/workflows/test.yml
```

### Adding New Checks

Edit `.pre-commit-config.yaml` to add new hooks.

Example:
```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
```

## Relationship with SAGE

- **Neuromem CI**: Lint, format, build validation (lightweight)
- **SAGE CI**: Full integration tests, coverage, deployment (comprehensive)

This separation keeps neuromem CI fast while ensuring comprehensive testing in SAGE.
