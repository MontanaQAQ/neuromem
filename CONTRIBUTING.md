# Quick Start: Neuromem CI/CD Setup

This guide helps you set up the CI/CD environment for neuromem development.

## For Contributors

### First-time Setup

#### Option 1: Automatic Setup (SAGE Developers - Recommended)

If you're working on neuromem as part of SAGE development:

```bash
cd /path/to/SAGE
./quickstart.sh --dev --yes
```

This will **automatically**:
- Install neuromem in editable mode
- Install pre-commit framework
- **Configure pre-commit hooks for neuromem** (no manual setup needed!)

#### Option 2: Manual Setup (Standalone Development)

```bash
# 1. Clone the repository
git clone https://github.com/intellistream/neuromem.git
cd neuromem

# 2. Install neuromem with dev dependencies
pip install -e .[dev]

# 3. Install pre-commit hooks (if not auto-installed)
pre-commit install

# 4. Test the setup
pre-commit run --all-files
```

**Note**: When you run `pip install -e .[dev]`, it will attempt to automatically
install pre-commit hooks if you're in a git repository.

### Daily Workflow

```bash
# Make your changes
vim memory_collection/your_file.py

# Stage your changes
git add .

# Commit (pre-commit hooks run automatically)
git commit -m "feat: add new feature"

# If hooks fail, fix the issues and try again
# Most formatting issues are auto-fixed
git add .
git commit -m "feat: add new feature"

# Push to remote
git push origin your-branch
```

### CI/CD Pipeline

When you push to GitHub:

1. **Lint Check** (runs in ~1 min)
   - Validates code style with ruff
   - Auto-formatting check

2. **Validation** (runs in ~1 min)
   - Checks pyproject.toml
   - Python syntax validation

3. **Build Check** (runs in ~2 min)
   - Builds Python package
   - Validates package structure

All checks must pass before merging.

## Handling Hook Failures

### Ruff Check Fails

```bash
# Auto-fix most issues
ruff check --fix .
ruff format .

# Re-stage and commit
git add .
git commit -m "your message"
```

### Syntax Error

Fix the Python syntax error in your code, then retry.

### File Check Fails

Pre-commit will auto-fix most file issues (whitespace, EOF, etc.).
Just re-stage and commit:

```bash
git add .
git commit -m "your message"
```

## Skip Hooks (Not Recommended)

```bash
# Only use in emergency
git commit --no-verify -m "urgent fix"
```

## Update Hooks

```bash
# Get latest hook versions
pre-commit autoupdate

# Test updated hooks
pre-commit run --all-files
```

## Troubleshooting

### "pre-commit: command not found"

```bash
pip install pre-commit
```

### Hooks not running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Permission denied

```bash
# Make hooks executable
chmod +x .git/hooks/pre-commit
```

## More Information

See [CI_CD_README.md](CI_CD_README.md) for detailed documentation.
