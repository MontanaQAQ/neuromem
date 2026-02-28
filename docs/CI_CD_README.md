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
- `pyproject.toml`: Requires `ruff>=0.1.0` in benchmark dependencies
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

### Workflow: `.github/workflows/benchmark.yml`

Purpose-built for the paper1 memory benchmarks that were ported from the SAGE benchmarks repo. The workflow can be triggered manually or via the nightly cron (UTC 02:00) and always runs on a self-hosted runner tagged `self-hosted` + `llm-server` with GPU + sageLLM access.

#### Runner requirements

- sageLLM/OpenAI-compatible LLM endpoint reachable from the runner (export `LLM_BASE_URL`, `LLM_MODEL_NAME`, `LLM_API_KEY` in the runner environment or pass them via workflow inputs)
- Hugging Face download token via `HF_TOKEN` environment variable (used to fetch datasets/models)
- Pre-installed benchmark dependencies (handled automatically by `pip install -e .[benchmark]`)
- Adequate disk space for `.sage/benchmarks` artifacts

#### Inputs

| Input | Description | Default |
| --- | --- | --- |
| `sections` | Comma separated logical sections (currently only `stm` is consumed) | `stm` |
| `experiments` | Comma separated task IDs such as `group-1` … `group-10` | All ten groups |
| `config_path` | Path to the YAML config inside the repo | `benchmarks/experiment/config/longmemeval_short_term_memory_pipeline.yaml` |
| `quick_mode` | Boolean flag to run only the first two tasks | `false` |
| `llm_base_url` | Optional override for `runtime.base_url` | empty |
| `llm_model_name` | Optional override for `runtime.model_name` | empty |
| `llm_api_key` | Optional override for `runtime.api_key` | empty |

Values coming from the inputs take precedence, but the workflow will fall back to environment variables (`LLM_BASE_URL`, `LLM_MODEL_NAME`, `LLM_API_KEY`) when inputs are blank. Configure these as encrypted environment variables on the self-hosted runner to avoid exposing secrets in dispatch forms.

#### What the job does

1. Checks out the repo, sets up Python 3.11, caches pip, and installs `.[benchmark]`.
2. Optionally installs the Hugging Face token (if `HF_TOKEN` is present) under `~/.huggingface/token`.
3. Copies the selected config, injects any runtime overrides (LLM endpoint/model/key), and stores a generated config under `benchmarks/experiment/config/generated/`.
4. Iterates over the requested task IDs (respecting `quick_mode`) and runs `benchmarks/experiment/memory_test_pipeline.py` for each task, mirroring the paper1 experiment flow.
5. Uploads `.sage/benchmarks/**` and `benchmarks/logs/**` as artifacts for downstream analysis.

All benchmark logs are available directly in the workflow logs, while structured JSON results live under `.sage/benchmarks/benchmark_memory/<dataset>/<timestamp>/<memory_name>/` inside the uploaded artifact.

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
2. **Build failures**: Check `pyproject.toml`
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
