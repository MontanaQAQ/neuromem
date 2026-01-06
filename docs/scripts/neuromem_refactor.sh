#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📦 NeuroMem 命名空间包重构脚本"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查当前目录
if [ ! -d "neuromem" ]; then
    echo "❌ 错误：当前目录没有 neuromem/ 文件夹"
    echo "   请在 NeuroMem 仓库根目录运行此脚本"
    exit 1
fi

echo "✅ 检测到 neuromem/ 目录"
echo ""

# 备份
echo "📦 创建备份..."
cp -r neuromem neuromem_backup
echo "✅ 备份完成: neuromem_backup/"
echo ""

# 步骤 1: 创建命名空间目录结构
echo "📁 步骤 1: 创建命名空间目录结构..."
mkdir -p sage/middleware/components/sage_mem

# 步骤 2: 使用 git mv 保留历史（如果是 git 仓库）
echo "📦 步骤 2: 移动 neuromem 到命名空间..."
if [ -d ".git" ]; then
    echo "   检测到 git 仓库，使用 git mv..."
    git mv neuromem sage/middleware/components/sage_mem/
else
    echo "   非 git 仓库，使用 mv..."
    mv neuromem sage/middleware/components/sage_mem/
fi

# 步骤 3: 创建命名空间标记文件
echo "�� 步骤 3: 创建命名空间标记文件..."

cat > sage/__init__.py << 'INIT'
"""SAGE namespace package"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
INIT

cat > sage/middleware/__init__.py << 'INIT'
"""SAGE middleware namespace package"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
INIT

cat > sage/middleware/components/__init__.py << 'INIT'
"""SAGE middleware components namespace package"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
INIT

cat > sage/middleware/components/sage_mem/__init__.py << 'INIT'
"""SAGE-Mem namespace package for memory management implementations"""
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
INIT

echo "✅ 命名空间标记文件创建完成"
echo ""

# 步骤 4: 更新 pyproject.toml
echo "📝 步骤 4: 更新 pyproject.toml..."
if [ -f "pyproject.toml" ]; then
    # 备份原文件
    cp pyproject.toml pyproject.toml.backup

    # 更新 packages.find
    sed -i 's/include = \["neuromem\*"\]/include = ["sage.middleware.components.sage_mem.neuromem*"]/' pyproject.toml

    # 添加 zip-safe 配置（如果不存在）
    if ! grep -q "zip-safe" pyproject.toml; then
        echo "" >> pyproject.toml
        echo "[tool.setuptools]" >> pyproject.toml
        echo "zip-safe = false" >> pyproject.toml
    fi

    echo "✅ pyproject.toml 更新完成"
else
    echo "⚠️  警告：未找到 pyproject.toml"
fi
echo ""

# 步骤 5: 验证 pyproject.toml 配置
echo "📝 步骤 5: 验证 pyproject.toml 配置..."
if [ -f "pyproject.toml" ]; then
    echo "✅ pyproject.toml 存在，检查包名是否为 'isage-neuromem'"
    grep -q 'name = "isage-neuromem"' pyproject.toml && echo "✅ 包名正确" || echo "⚠️  请检查 pyproject.toml 中的包名"
else
    echo "⚠️  pyproject.toml 不存在，请创建该文件"
fi
echo ""

# 步骤 6: 验证包结构
echo "🔍 步骤 6: 验证包结构..."
python3 << 'VERIFY'
from setuptools import find_packages

packages = find_packages(
    where=".",
    include=["sage.middleware.components.sage_mem.neuromem*"],
    exclude=["tests*", "examples*"]
)

print("\n✅ 找到的包:")
for pkg in sorted(packages):
    print(f"  - {pkg}")

if len(packages) > 0:
    print(f"\n✅ 总共找到 {len(packages)} 个包")
else:
    print("\n❌ 错误：未找到任何包")
    exit(1)
VERIFY

echo ""

# 步骤 7: 显示新结构
echo "📂 步骤 7: 新的目录结构:"
tree sage/ -L 4 2>/dev/null || find sage/ -type d | head -20

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 重构完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 后续步骤:"
echo ""
echo "1. 更新导入语句 (examples, tests, README.md):"
echo "   旧: from neuromem import MemoryManager"
echo "   新: from sage.middleware.components.sage_mem.neuromem import MemoryManager"
echo ""
echo "2. 构建和测试:"
echo "   python3 -m build"
echo "   pip install -e ."
echo ""
echo "3. 验证导入:"
echo "   python3 -c 'from sage.middleware.components.sage_mem.neuromem import MemoryManager; print(MemoryManager)'"
echo ""
echo "4. 提交更改:"
echo "   git add sage/"
echo "   git commit -m 'refactor: convert to SAGE namespace package'"
echo ""
echo "📦 备份位置: neuromem_backup/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
