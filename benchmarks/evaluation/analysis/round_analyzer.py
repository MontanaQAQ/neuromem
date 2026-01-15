#!/usr/bin/env python3
"""
通用轮次分析器

基于配置文件驱动的分析脚本，支持多种数据集

使用方法:
    # 分析指定目录
    python round_analyzer.py --config locomo --path PostInsert_MemoryOS_forgetting_curve

    # 分析所有目录
    python round_analyzer.py --config locomo --all

    # 指定前缀
    python round_analyzer.py --config locomo --prefix PostInsert_
"""

from __future__ import annotations

import argparse
import csv
import datetime
import sys
from pathlib import Path

import numpy as np
import yaml

# 支持直接运行和作为模块导入
try:
    from .utils.data_loader import DataLoader, RoundAnalyzer
    from .utils.plotting import plot_comparison, plot_single_strategy
    from .utils.validators import (
        discover_experiment_dirs,
        print_validation_report,
        validate_experiment_dir,
    )
except ImportError:
    from utils.data_loader import DataLoader, RoundAnalyzer
    from utils.plotting import plot_comparison, plot_single_strategy
    from utils.validators import (
        discover_experiment_dirs,
        print_validation_report,
        validate_experiment_dir,
    )


def load_config(config_name: str) -> dict:
    """加载配置文件"""
    config_dir = Path(__file__).parent / "config"
    config_file = config_dir / f"{config_name}.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_file}")

    with open(config_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_project_root() -> Path:
    """获取项目根目录（从analysis目录向上3级）"""
    # analysis -> evaluation -> benchmarks -> project_root
    return Path(__file__).parent.parent.parent.parent


def resolve_path(path: str) -> Path:
    """解析相对路径为绝对路径"""
    if Path(path).is_absolute():
        return Path(path)
    return get_project_root() / path


def run_analysis(
    config: dict,
    strategies: list[str],
    base_dir: str | None = None,
    output_dir: str | None = None,
    validate_only: bool = False,
):
    """
    执行分析

    Args:
        config: 配置字典
        strategies: 要分析的策略列表
        base_dir: 数据目录（覆盖配置）
        output_dir: 输出目录（覆盖配置）
        validate_only: 仅验证不分析
    """
    # 解析路径（支持相对于项目根目录的路径）
    base_path = resolve_path(base_dir or config["paths"]["base_dir"])
    out_path = resolve_path(output_dir or config["paths"]["output_dir"])

    if not base_path.exists():
        print(f"错误: 数据目录不存在: {base_path}")
        sys.exit(1)

    out_path.mkdir(parents=True, exist_ok=True)

    # 验证数据
    print("=" * 70)
    print("数据验证")
    print("=" * 70)

    validation_results = []
    valid_strategies = []

    for strategy in strategies:
        result = validate_experiment_dir(base_path / strategy)
        validation_results.append(result)
        if result["valid"]:
            valid_strategies.append(strategy)

    print_validation_report(validation_results)

    if validate_only:
        return

    if not valid_strategies:
        print("错误: 没有有效的策略目录")
        sys.exit(1)

    # 初始化分析器
    evaluator_name = config.get("evaluator", {}).get("name", "generic_f1")
    loader = DataLoader(base_path)
    analyzer = RoundAnalyzer(evaluator_name)

    print("=" * 70)
    print(f"开始分析 ({len(valid_strategies)} 个策略)")
    print("=" * 70)

    # 存储所有指标
    all_f1 = {}
    all_insert = {}
    all_retrieval = {}

    for strategy in valid_strategies:
        print(f"\n[{strategy}]")

        # 聚合指标
        f1_metrics = analyzer.aggregate_across_tasks(loader, strategy, "f1")
        insert_metrics = analyzer.aggregate_across_tasks(loader, strategy, "insert_time")
        retrieval_metrics = analyzer.aggregate_across_tasks(loader, strategy, "retrieval_time")

        print(f"  F1 Scores: {f1_metrics}")
        print(f"  Insert Times (ms): {insert_metrics}")
        print(f"  Retrieval Times (ms): {retrieval_metrics}")

        all_f1[strategy] = f1_metrics
        all_insert[strategy] = insert_metrics
        all_retrieval[strategy] = retrieval_metrics

        # 绘制单策略图
        if config.get("output", {}).get("charts", {}).get("single_strategy", True):
            plot_single_strategy(
                strategy,
                f1_metrics,
                insert_metrics,
                retrieval_metrics,
                out_path / f"{strategy}_metrics.png",
            )
            print(f"  ✓ Saved: {strategy}_metrics.png")

    # 绘制对比图
    print("\n[Comparison Charts]")

    if config.get("output", {}).get("charts", {}).get("comparison", True):
        plot_comparison(all_f1, "F1 Score", "F1 Score", out_path / "comparison_f1.png")
        print("  ✓ Saved: comparison_f1.png")

        plot_comparison(
            all_insert, "Insert Time", "Time (ms)", out_path / "comparison_insert_time.png"
        )
        print("  ✓ Saved: comparison_insert_time.png")

        plot_comparison(
            all_retrieval, "Retrieval Time", "Time (ms)", out_path / "comparison_retrieval_time.png"
        )
        print("  ✓ Saved: comparison_retrieval_time.png")

    # 生成CSV
    if "csv" in config.get("output", {}).get("formats", []):
        generate_csv(all_f1, out_path / "f1_scores.csv", "F1")
        generate_csv(all_insert, out_path / "insert_times.csv", "Insert Time (ms)")
        generate_csv(all_retrieval, out_path / "retrieval_times.csv", "Retrieval Time (ms)")
        print("\n✓ CSV files saved")

    # 生成Markdown报告
    if "md" in config.get("output", {}).get("formats", []):
        generate_markdown(
            config,
            valid_strategies,
            all_f1,
            all_insert,
            all_retrieval,
            out_path / "analysis_report.md",
        )
        print("✓ Markdown report saved")

    print(f"\n{'=' * 70}")
    print(f"分析完成! 结果保存至: {out_path}")
    print(f"{'=' * 70}")


def generate_csv(
    metrics: dict[str, dict[int, float]],
    output_path: Path,
    metric_name: str,
):
    """生成CSV文件"""
    if not metrics:
        return

    # 获取所有轮次
    all_rounds = sorted(set().union(*[set(m.keys()) for m in metrics.values()]))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # 表头
        header = ["Strategy"] + [f"R{r}" for r in all_rounds] + ["Mean"]
        writer.writerow(header)

        # 数据行
        for strategy, round_metrics in metrics.items():
            values = [round_metrics.get(r, 0) for r in all_rounds]
            mean_val = float(np.mean(values)) if values else 0
            row = (
                [strategy]
                + [f"{v:.6f}" if v < 1 else f"{v:.2f}" for v in values]
                + [f"{mean_val:.6f}" if mean_val < 1 else f"{mean_val:.2f}"]
            )
            writer.writerow(row)


def generate_markdown(
    config: dict,
    strategies: list[str],
    f1_metrics: dict,
    insert_metrics: dict,
    retrieval_metrics: dict,
    output_path: Path,
):
    """生成Markdown报告"""
    dataset_name = config.get("dataset", {}).get("name", "Unknown")

    # 获取所有轮次
    all_rounds = sorted(set().union(*[set(m.keys()) for m in f1_metrics.values()]))

    md = f"# {dataset_name.upper()} Round Analysis Report\n\n"
    md += f"**Generated:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    md += "## Summary\n\n"
    md += f"- **Dataset:** {dataset_name}\n"
    md += f"- **Strategies:** {len(strategies)}\n"
    md += f"- **Rounds:** {len(all_rounds)}\n\n"

    # F1对比表
    md += "## F1 Scores\n\n"
    md += "| Strategy | " + " | ".join([f"R{r}" for r in all_rounds]) + " | Mean |\n"
    md += "|----------|" + "|".join(["------" for _ in all_rounds]) + "|------|\n"

    for strategy in strategies:
        vals = [f1_metrics.get(strategy, {}).get(r, 0) for r in all_rounds]
        mean_val = float(np.mean(vals)) if vals else 0
        md += f"| {strategy} | " + " | ".join([f"{v:.4f}" for v in vals]) + f" | {mean_val:.4f} |\n"

    md += "\n"

    # Insert时间表
    md += "## Insert Time (ms)\n\n"
    md += "| Strategy | " + " | ".join([f"R{r}" for r in all_rounds]) + " | Mean |\n"
    md += "|----------|" + "|".join(["------" for _ in all_rounds]) + "|------|\n"

    for strategy in strategies:
        vals = [insert_metrics.get(strategy, {}).get(r, 0) for r in all_rounds]
        mean_val = float(np.mean(vals)) if vals else 0
        md += f"| {strategy} | " + " | ".join([f"{v:.2f}" for v in vals]) + f" | {mean_val:.2f} |\n"

    md += "\n"

    # Retrieval时间表
    md += "## Retrieval Time (ms)\n\n"
    md += "| Strategy | " + " | ".join([f"R{r}" for r in all_rounds]) + " | Mean |\n"
    md += "|----------|" + "|".join(["------" for _ in all_rounds]) + "|------|\n"

    for strategy in strategies:
        vals = [retrieval_metrics.get(strategy, {}).get(r, 0) for r in all_rounds]
        mean_val = float(np.mean(vals)) if vals else 0
        md += f"| {strategy} | " + " | ".join([f"{v:.2f}" for v in vals]) + f" | {mean_val:.2f} |\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


def main():
    parser = argparse.ArgumentParser(
        description="通用轮次分析器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析LoCoMo的指定目录
  python round_analyzer.py --config locomo --path PostInsert_MemoryOS_forgetting_curve

  # 分析所有PostInsert目录
  python round_analyzer.py --config locomo --all --prefix PostInsert_

  # 仅验证数据
  python round_analyzer.py --config locomo --all --validate-only
        """,
    )

    parser.add_argument(
        "--config",
        required=True,
        help="配置文件名（不含.yaml后缀）",
    )
    parser.add_argument(
        "--path",
        nargs="+",
        help="要分析的目录名称",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="分析所有匹配前缀的目录",
    )
    parser.add_argument(
        "--prefix",
        default="PostInsert_",
        help="目录前缀（默认: PostInsert_）",
    )
    parser.add_argument(
        "--base-dir",
        help="数据基础目录（覆盖配置）",
    )
    parser.add_argument(
        "--output-dir",
        help="输出目录（覆盖配置）",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="仅验证数据，不执行分析",
    )

    args = parser.parse_args()

    # 加载配置
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    # 解析基础目录路径
    base_dir = resolve_path(args.base_dir or config["paths"]["base_dir"])

    # 确定要分析的策略
    if args.all:
        strategies = discover_experiment_dirs(base_dir, args.prefix)
        if not strategies:
            print(f"错误: 未找到以 '{args.prefix}' 开头的目录")
            sys.exit(1)
    elif args.path:
        strategies = args.path
    else:
        print("错误: 请指定 --path 或 --all")
        parser.print_help()
        sys.exit(1)

    run_analysis(
        config,
        strategies,
        base_dir=str(base_dir),
        output_dir=args.output_dir,
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    main()
