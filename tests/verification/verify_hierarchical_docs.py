#!/usr/bin/env python3
"""Standalone 验证脚本

验证 neuromem 仓库内 Hierarchical Services 文档与测试完整性。
"""

import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[2]
DOCS_DIR = ROOT / "docs" / "services"
HIERARCHICAL_DOCS_DIR = DOCS_DIR / "hierarchical"
UNIT_TEST_DIR = ROOT / "tests" / "unit" / "neuromem" / "services"
INTEGRATION_TEST_DIR = ROOT / "tests" / "integration" / "services"


def check_file_exists(path: Path, description: str) -> bool:
    """检查文件是否存在"""
    if path.exists():
        print(f"✅ {description}: {path.name}")
        return True
    print(f"❌ {description} 缺失: {path}")
    return False


def check_documentation():
    """检查文档完整性"""
    print("\n" + "=" * 60)
    print("1. 检查文档文件")
    print("=" * 60)

    checks = [
        (DOCS_DIR / "SERVICES_README.md", "Services 总览文档"),
        (DOCS_DIR / "API_REFERENCE.md", "API 参考文档"),
        (DOCS_DIR / "BENCHMARKS.md", "性能基准文档"),
        (HIERARCHICAL_DOCS_DIR / "README.md", "Hierarchical 完整文档"),
        (HIERARCHICAL_DOCS_DIR / "QUICKSTART.md", "Hierarchical 快速开始"),
    ]

    results = [check_file_exists(path, desc) for path, desc in checks]
    return all(results)


def check_tests():
    """检查测试文件"""
    print("\n" + "=" * 60)
    print("2. 检查测试文件")
    print("=" * 60)

    checks = [
        (UNIT_TEST_DIR / "test_linknote_graph.py", "Linknote 单元测试"),
        (UNIT_TEST_DIR / "test_property_graph.py", "PropertyGraph 单元测试"),
        (
            INTEGRATION_TEST_DIR / "test_hierarchical_services_integration.py",
            "Hierarchical 集成测试",
        ),
    ]

    results = [check_file_exists(path, desc) for path, desc in checks]
    return all(results)


def check_content():
    """检查文档内容完整性"""
    print("\n" + "=" * 60)
    print("3. 检查文档内容")
    print("=" * 60)

    readme = HIERARCHICAL_DOCS_DIR / "README.md"
    if readme.exists():
        content = readme.read_text()
        required_sections = [
            "# Hierarchical Services",
            "## 概述",
            "## 快速开始",
            "## 核心功能",
            "## 高级用法",
            "## API 参考",
        ]

        missing = [s for s in required_sections if s not in content]
        if not missing:
            print("✅ README.md 包含所有必需章节")
        else:
            print(f"❌ README.md 缺少章节: {missing}")
            return False

    quickstart = HIERARCHICAL_DOCS_DIR / "QUICKSTART.md"
    if quickstart.exists():
        content = quickstart.read_text()
        required_sections = [
            "# Hierarchical Services 快速开始",
            "## 场景 1: 笔记链接",
            "## 场景 2: 知识图谱",
            "## 核心 API 速查",
        ]

        missing = [s for s in required_sections if s not in content]
        if not missing:
            print("✅ QUICKSTART.md 包含所有必需章节")
        else:
            print(f"❌ QUICKSTART.md 缺少章节: {missing}")
            return False

    return True


def print_statistics():
    """打印统计信息"""
    print("\n" + "=" * 60)
    print("4. 统计信息")
    print("=" * 60)

    readme_lines = (
        len((HIERARCHICAL_DOCS_DIR / "README.md").read_text().split("\n"))
        if (HIERARCHICAL_DOCS_DIR / "README.md").exists()
        else 0
    )
    quickstart_lines = (
        len((HIERARCHICAL_DOCS_DIR / "QUICKSTART.md").read_text().split("\n"))
        if (HIERARCHICAL_DOCS_DIR / "QUICKSTART.md").exists()
        else 0
    )

    print(f"README.md: {readme_lines} 行")
    print(f"QUICKSTART.md: {quickstart_lines} 行")
    print(f"文档总行数: {readme_lines + quickstart_lines} 行")

    service_tests = sorted(UNIT_TEST_DIR.glob("test_*.py"))
    print(f"\nservices 单元测试文件数: {len(service_tests)}")
    for test_file in service_tests:
        print(f"  - {test_file.name}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("T2.8 完善文档和示例 - 验证脚本")
    print("=" * 60)

    results = []

    # 执行所有检查
    results.append(check_documentation())
    results.append(check_tests())
    results.append(check_content())

    # 统计信息
    print_statistics()

    # 总结
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    if all(results):
        print("✅ 所有检查通过！T2.8 完成。")
        return 0
    print("❌ 部分检查失败，请修复问题。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
