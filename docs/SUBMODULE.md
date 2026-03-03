# Repository Workflow: neuromem

neuromem 现在是独立仓库，不再作为旧集中仓库结构下的 Git submodule 维护。

## Repository Information

- **Repository:** https://github.com/intellistream/neuromem.git
- **Default development branch:** `main-dev`
- **Local root:** repository root directory

## Quick Guide for Committing Changes

```bash
# 在 neuromem 仓库根目录
git add .
git commit -m "feat: your change description"
git push origin main-dev
```

## Updating Local Branch

```bash
git checkout main-dev
git pull --ff-only origin main-dev
```

## Common Issues

### ❌ Detached HEAD

```bash
git checkout main-dev
git pull --ff-only origin main-dev
```

### ❌ Push rejected

```bash
git fetch origin
git rebase origin/main-dev
git push origin main-dev
```

## Development Workflow

1. 在 `main-dev` 上开发并提交。
2. 本仓库内完成测试与质量检查后再推送。
3. 通过 PR 将 `main-dev` 合并到 `main`。
