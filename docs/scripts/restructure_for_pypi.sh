#!/bin/bash
set -e

echo "🔧 Restructuring neuromem for PyPI packaging..."

# 1. Create neuromem subdirectory
mkdir -p neuromem_new

# 2. Move Python packages to neuromem_new/
for dir in memory_collection search_engine storage_engine services utils config; do
    if [ -d "$dir" ]; then
        echo "  📦 Moving $dir..."
        mv "$dir" neuromem_new/
    fi
done

# 3. Move core Python files
for file in __init__.py _version.py memory_manager.py; do
    if [ -f "$file" ]; then
        echo "  📄 Moving $file..."
        mv "$file" neuromem_new/
    fi
done

# 4. Rename neuromem_new to neuromem
mv neuromem_new neuromem

echo "✅ Restructuring complete!"
echo "📂 New structure:"
ls -la neuromem/
