#!/usr/bin/env python3
"""
Generate unified 3-column figure comparing Memory Data Structure (D1) performance
across LOCOMO, LONGMEMEVAL, and MEMORYAGENTBENCH benchmarks.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Data structure mapping for cleaner display names
DS_DISPLAY_NAMES = {
    "DataStructure_inverted_vectorstore": "Hybrid (Inverted+Vector)",
    "DataStructure_feature_queue_vectorstore": "Queue+Vector",
    "DataStructure_feature_queue_segment": "Queue+Segment",
    "DataStructure_feature_queue_summary": "Queue+Summary",
    "DataStructure_feature_summary_vectorstore": "Summary+Vector",
    "DataStructure_semantic_inverted_kg": "Semantic KG",
    "DataStructure_linknote_graph": "LinkNote Graph",
    "DataStructure_property_graph": "Property Graph",
    "DataStructure_fifo_queue": "FIFO Queue",
    "DataStructure_segment": "Segment",
    "DataStructure_lsh_hash": "LSH Hash",
}

# Consistent marker styles and colors for each data structure
DS_STYLES = {
    "DataStructure_inverted_vectorstore": {
        "marker": "*",
        "color": "#e74c3c",
        "size": 300,
        "label": "Hybrid (Inverted+Vector)",
    },  # Red star - highlight
    "DataStructure_feature_queue_vectorstore": {
        "marker": "D",
        "color": "#3498db",
        "size": 100,
        "label": "Queue+Vector",
    },
    "DataStructure_feature_queue_segment": {
        "marker": "s",
        "color": "#2ecc71",
        "size": 100,
        "label": "Queue+Segment",
    },
    "DataStructure_feature_queue_summary": {
        "marker": "^",
        "color": "#9b59b6",
        "size": 100,
        "label": "Queue+Summary",
    },
    "DataStructure_feature_summary_vectorstore": {
        "marker": "v",
        "color": "#f39c12",
        "size": 100,
        "label": "Summary+Vector",
    },
    "DataStructure_semantic_inverted_kg": {
        "marker": "p",
        "color": "#1abc9c",
        "size": 100,
        "label": "Semantic KG",
    },
    "DataStructure_linknote_graph": {
        "marker": "h",
        "color": "#34495e",
        "size": 100,
        "label": "LinkNote Graph",
    },
    "DataStructure_property_graph": {
        "marker": "H",
        "color": "#95a5a6",
        "size": 100,
        "label": "Property Graph",
    },
    "DataStructure_fifo_queue": {
        "marker": "o",
        "color": "#e67e22",
        "size": 80,
        "label": "FIFO Queue",
    },
    "DataStructure_segment": {"marker": "X", "color": "#d35400", "size": 100, "label": "Segment"},
    "DataStructure_lsh_hash": {"marker": "P", "color": "#7f8c8d", "size": 100, "label": "LSH Hash"},
}


def compute_pareto_frontier(latencies, f1_scores):
    """
    Compute the Pareto frontier (lower latency, higher F1 is better).
    Returns indices of points on the frontier, sorted by latency.
    """
    points = np.column_stack([latencies, f1_scores])
    pareto_indices = []

    for i, (lat, f1) in enumerate(points):
        is_pareto = True
        for j, (other_lat, other_f1) in enumerate(points):
            # Another point dominates if it has both lower latency and higher F1
            if (
                i != j
                and other_lat <= lat
                and other_f1 >= f1
                and (other_lat < lat or other_f1 > f1)
            ):
                is_pareto = False
                break
        if is_pareto:
            pareto_indices.append(i)

    # Sort by latency for smooth curve
    return sorted(pareto_indices, key=lambda i: latencies[i])


def load_benchmark_data(benchmark_name):
    """Load F1 scores and retrieval times for a benchmark."""
    base_path = Path(
        f".sage/benchmarks/benchmark_memory/{benchmark_name}/output/round_analysis_datastructure"
    )

    f1_df = pd.read_csv(base_path / "f1_scores.csv")
    retrieval_df = pd.read_csv(base_path / "retrieval_times.csv")

    # Use mean values
    data = []
    for _idx, row in f1_df.iterrows():
        strategy = row["Strategy"]
        f1_mean = row["Mean"]
        retrieval_mean = retrieval_df[retrieval_df["Strategy"] == strategy]["Mean"].values[0]
        data.append({"strategy": strategy, "f1": f1_mean, "retrieval_latency": retrieval_mean})

    return pd.DataFrame(data)


def create_unified_comparison():
    """Create the unified 3-column comparison figure."""

    # Load data for all three benchmarks
    locomo_data = load_benchmark_data("locomo")
    longmemeval_data = load_benchmark_data("longmemeval")
    conflict_data = load_benchmark_data("conflict_resolution")

    # Create figure with 1 row, 3 columns
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5))

    datasets = [
        (locomo_data, "LOCOMO", axes[0]),
        (longmemeval_data, "LONGMEMEVAL", axes[1]),
        (conflict_data, "MemAgentBench", axes[2]),
    ]

    for data, title, ax in datasets:
        # Plot each data structure
        for _, row in data.iterrows():
            strategy = row["strategy"]
            if strategy not in DS_STYLES:
                continue

            style = DS_STYLES[strategy]
            ax.scatter(
                row["retrieval_latency"],
                row["f1"],
                marker=style["marker"],
                color=style["color"],
                s=style["size"],
                alpha=0.8,
                edgecolors="black",
                linewidths=1.5 if strategy == "DataStructure_inverted_vectorstore" else 1,
                zorder=10 if strategy == "DataStructure_inverted_vectorstore" else 5,
            )

        # Compute and draw Pareto frontier
        latencies = data["retrieval_latency"].values
        f1_scores = data["f1"].values
        pareto_indices = compute_pareto_frontier(latencies, f1_scores)

        if len(pareto_indices) > 1:
            pareto_latencies = [latencies[i] for i in pareto_indices]
            pareto_f1s = [f1_scores[i] for i in pareto_indices]
            ax.plot(
                pareto_latencies,
                pareto_f1s,
                "k--",
                alpha=0.3,
                linewidth=1.5,
                label="Efficiency Frontier",
                zorder=1,
            )

        # Use linear scale (data range is not large enough to require log)
        # ax.set_xscale('log')  # Disabled - linear is clearer for this data

        # Let matplotlib auto-determine ticks, just set reasonable limits
        x_vals = data["retrieval_latency"].values
        x_min, x_max = x_vals.min(), x_vals.max()
        x_margin = (x_max - x_min) * 0.1
        ax.set_xlim(x_min - x_margin, x_max + x_margin)

        # Tick label settings
        ax.tick_params(axis="x", which="major", labelsize=16, rotation=0, length=5)

        # Labels and title
        ax.set_xlabel("Retrieval Latency (ms)", fontsize=18, fontweight="bold")
        if ax == axes[0]:  # Only leftmost plot gets y-label
            ax.set_ylabel("Token-level F1 Score", fontsize=18, fontweight="bold")
        ax.set_title(title, fontsize=20, fontweight="bold", pad=10)

        # Grid
        ax.grid(True, alpha=0.3, linestyle=":", linewidth=0.5, which="major")
        ax.grid(True, alpha=0.15, linestyle=":", linewidth=0.3, which="minor")
        ax.set_axisbelow(True)

        # Improve tick labels
        ax.tick_params(axis="y", which="major", labelsize=16)

    # Create unified legend below the plots
    handles = []
    labels = []
    for strategy, style in DS_STYLES.items():
        if strategy in locomo_data["strategy"].values:
            handle = plt.Line2D(
                [0],
                [0],
                marker=style["marker"],
                color="w",
                markerfacecolor=style["color"],
                markersize=16,
                markeredgecolor="black",
                markeredgewidth=1.5 if strategy == "DataStructure_inverted_vectorstore" else 1,
                label=style["label"],
            )
            handles.append(handle)
            labels.append(style["label"])

    # Add Pareto frontier to legend
    handles.append(plt.Line2D([0], [0], color="k", linestyle="--", alpha=0.3, linewidth=2))
    labels.append("Efficiency Frontier")

    # Position legend below the plots - 2 rows with 6 columns
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=6,
        bbox_to_anchor=(0.5, -0.03),
        fontsize=16,
        frameon=True,
        fancybox=True,
        shadow=True,
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.21)  # Make room for 2-row legend

    # Save figure
    output_dir = Path(".sage/benchmark_paper/Figures/Experiment/DataStructure")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "unified_d1_comparison_3benchmarks.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✓ Figure saved to: {output_path}")

    # Also save as PDF for paper
    output_path_pdf = output_dir / "unified_d1_comparison_3benchmarks.pdf"
    plt.savefig(output_path_pdf, bbox_inches="tight")
    print(f"✓ PDF version saved to: {output_path_pdf}")

    plt.close()

    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY: Memory Data Structure (D1) Cross-Benchmark Performance")
    print("=" * 80)

    for data, name in [
        (locomo_data, "LOCOMO"),
        (longmemeval_data, "LONGMEMEVAL"),
        (conflict_data, "MEMORYAGENTBENCH"),
    ]:
        print(f"\n{name}:")
        top3 = data.nlargest(3, "f1")
        for _idx, row in top3.iterrows():
            strategy_name = DS_DISPLAY_NAMES.get(row["strategy"], row["strategy"])
            print(
                f"  {strategy_name:35s} F1={row['f1']:.4f}  Latency={row['retrieval_latency']:6.1f}ms"
            )


if __name__ == "__main__":
    create_unified_comparison()
