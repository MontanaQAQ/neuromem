"""
绘图工具

职责:
- 提供通用的绑图函数
- 支持单策略和多策略对比图
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")


# 默认颜色方案
DEFAULT_COLORS = [
    "#3498DB",  # 蓝色
    "#E74C3C",  # 红色
    "#2ECC71",  # 绿色
    "#9B59B6",  # 紫色
    "#F39C12",  # 橙色
    "#1ABC9C",  # 青色
    "#E91E63",  # 粉色
    "#795548",  # 棕色
]


def plot_comparison(
    strategies_metrics: dict[str, dict[int, float]],
    metric_name: str,
    ylabel: str,
    output_path: Path | str,
    title: str | None = None,
    figsize: tuple = (12, 7),
):
    """
    绘制多个策略的对比图

    Args:
        strategies_metrics: {strategy_name: {round_idx: value}}
        metric_name: 指标名称（用于标题）
        ylabel: Y轴标签
        output_path: 输出文件路径
        title: 自定义标题
        figsize: 图片尺寸
    """
    fig, ax = plt.subplots(figsize=figsize)

    colors = plt.cm.Set3(np.linspace(0, 1, max(len(strategies_metrics), 8)))

    for (strategy, metrics), color in zip(strategies_metrics.items(), colors):
        if not metrics:
            continue

        rounds = sorted(metrics.keys())
        values = [metrics[r] for r in rounds]

        ax.plot(
            rounds,
            values,
            marker="o",
            label=strategy,
            color=color,
            linewidth=2.5,
            markersize=8,
            alpha=0.8,
        )

    ax.set_xlabel("Test Round", fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=13, fontweight="bold")
    ax.set_title(
        title or f"{metric_name} by Round",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )

    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc="best")

    # 设置x轴刻度
    all_rounds = set()
    for m in strategies_metrics.values():
        all_rounds.update(m.keys())
    if all_rounds:
        ax.set_xticks(sorted(all_rounds))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_single_strategy(
    strategy_name: str,
    f1_metrics: dict[int, float],
    insert_metrics: dict[int, float],
    retrieval_metrics: dict[int, float],
    output_path: Path | str,
):
    """
    为单个策略绘制3个指标的子图

    Args:
        strategy_name: 策略名称
        f1_metrics: F1分数 {round: score}
        insert_metrics: 插入时间 {round: ms}
        retrieval_metrics: 检索时间 {round: ms}
        output_path: 输出文件路径
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 获取所有轮次
    all_rounds = sorted(
        set(f1_metrics.keys()) | set(insert_metrics.keys()) | set(retrieval_metrics.keys())
    )

    # F1分数
    f1_values = [f1_metrics.get(r, 0) for r in all_rounds]
    axes[0].plot(
        all_rounds,
        f1_values,
        marker="o",
        color="#3498DB",
        linewidth=2.5,
        markersize=10,
    )
    axes[0].set_xlabel("Test Round", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("F1 Score", fontsize=12, fontweight="bold")
    axes[0].set_title("F1 Score by Round", fontsize=13, fontweight="bold")
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xticks(all_rounds)

    # Insert时间
    insert_values = [insert_metrics.get(r, 0) for r in all_rounds]
    axes[1].plot(
        all_rounds,
        insert_values,
        marker="s",
        color="#E74C3C",
        linewidth=2.5,
        markersize=10,
    )
    axes[1].set_xlabel("Test Round", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("Time (ms)", fontsize=12, fontweight="bold")
    axes[1].set_title("Insert Time per Item (avg)", fontsize=13, fontweight="bold")
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xticks(all_rounds)

    # Retrieval时间
    retrieval_values = [retrieval_metrics.get(r, 0) for r in all_rounds]
    axes[2].plot(
        all_rounds,
        retrieval_values,
        marker="^",
        color="#2ECC71",
        linewidth=2.5,
        markersize=10,
    )
    axes[2].set_xlabel("Test Round", fontsize=12, fontweight="bold")
    axes[2].set_ylabel("Time (ms)", fontsize=12, fontweight="bold")
    axes[2].set_title("Retrieval Time per Query (avg)", fontsize=13, fontweight="bold")
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xticks(all_rounds)

    fig.suptitle(f"Strategy: {strategy_name}", fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_bar_comparison(
    data: dict[str, float],
    ylabel: str,
    output_path: Path | str,
    title: str = "",
    figsize: tuple = (10, 6),
):
    """
    绘制柱状对比图

    Args:
        data: {label: value}
        ylabel: Y轴标签
        output_path: 输出路径
        title: 标题
    """
    fig, ax = plt.subplots(figsize=figsize)

    labels = list(data.keys())
    values = list(data.values())
    colors = DEFAULT_COLORS[: len(labels)]

    bars = ax.bar(range(len(labels)), values, color=colors, alpha=0.8)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
    ax.set_ylabel(ylabel, fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # 添加数值标签
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{val:.3f}" if val < 10 else f"{val:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
