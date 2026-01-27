#!/usr/bin/env python3
"""
快速对比分析：bge-m3 vs e5-large-v2

直接从实验结果中提取关键指标，生成简洁的对比报告。
"""

import json
import statistics
from pathlib import Path


def load_results(result_dir: Path) -> list[dict]:
    """加载实验结果"""
    results = []
    if not result_dir.exists():
        return results

    for task_dir in sorted(result_dir.iterdir()):
        if not task_dir.is_dir():
            continue

        qa_file = task_dir / "qa_results.json"
        if qa_file.exists():
            with open(qa_file) as f:
                data = json.load(f)
                results.append(data)

    return results


def calculate_f1(prediction: str, reference: str) -> float:
    """简单的 Token-level F1 计算"""
    pred_tokens = set(prediction.lower().split())
    ref_tokens = set(reference.lower().split())

    if not pred_tokens and not ref_tokens:
        return 1.0
    if not pred_tokens or not ref_tokens:
        return 0.0

    common = pred_tokens & ref_tokens
    precision = len(common) / len(pred_tokens) if pred_tokens else 0
    recall = len(common) / len(ref_tokens) if ref_tokens else 0

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


def analyze_strategy(strategy_name: str, base_dir: Path) -> dict:
    """分析单个策略的结果"""
    strategy_dir = base_dir / strategy_name
    results = load_results(strategy_dir)

    if not results:
        return {
            "name": strategy_name,
            "f1_scores": [],
            "avg_f1": 0.0,
            "retrieval_times": [],
            "avg_retrieval_time": 0.0,
        }

    all_f1 = []
    all_retrieval_times = []

    for result in results:
        qa_pairs = result.get("qa_pairs", [])
        for qa in qa_pairs:
            pred = qa.get("predicted_answer", "")
            ref = qa.get("ground_truth", "")
            f1 = calculate_f1(pred, ref)
            all_f1.append(f1)

            # 提取检索时间
            retrieval_time = qa.get("retrieval_time_ms", 0)
            all_retrieval_times.append(retrieval_time)

    return {
        "name": strategy_name,
        "f1_scores": all_f1,
        "avg_f1": statistics.mean(all_f1) if all_f1 else 0.0,
        "std_f1": statistics.stdev(all_f1) if len(all_f1) > 1 else 0.0,
        "retrieval_times": all_retrieval_times,
        "avg_retrieval_time": statistics.mean(all_retrieval_times) if all_retrieval_times else 0.0,
        "task_count": len(results),
    }


def print_comparison(strategies: list[dict]):
    """打印对比报告"""
    print("=" * 80)
    print("补充实验：Embedding 模型对比分析")
    print("=" * 80)
    print()

    # 提取对比组
    bge_none = next(
        (s for s in strategies if "Mem0g_none" in s["name"] and "Additional" not in s["name"]), None
    )
    e5_none = next((s for s in strategies if "none_e5_large" in s["name"]), None)
    bge_rewrite = next(
        (s for s in strategies if "rewrite" in s["name"] and "Additional" not in s["name"]), None
    )
    e5_rewrite = next((s for s in strategies if "rewrite_e5_large" in s["name"]), None)

    # None 策略对比
    if bge_none and e5_none:
        print("【None 策略 - Embedding 对比】")
        print(f"  bge-m3:      F1 = {bge_none['avg_f1']:.4f} (±{bge_none.get('std_f1', 0):.4f})")
        print(f"  e5-large-v2: F1 = {e5_none['avg_f1']:.4f} (±{e5_none.get('std_f1', 0):.4f})")
        delta_f1 = e5_none["avg_f1"] - bge_none["avg_f1"]
        print(f"  Δ F1:        {delta_f1:+.4f} ({delta_f1 / bge_none['avg_f1'] * 100:+.2f}%)")
        print()
        print(f"  bge-m3:      Retrieval = {bge_none['avg_retrieval_time']:.2f} ms")
        print(f"  e5-large-v2: Retrieval = {e5_none['avg_retrieval_time']:.2f} ms")
        delta_time = e5_none["avg_retrieval_time"] - bge_none["avg_retrieval_time"]
        print(
            f"  Δ Time:      {delta_time:+.2f} ms ({delta_time / bge_none['avg_retrieval_time'] * 100:+.2f}%)"
        )
        print()

    # Rewrite 策略对比
    if bge_rewrite and e5_rewrite:
        print("【Rewrite 策略 - Embedding 对比】")
        print(
            f"  bge-m3:      F1 = {bge_rewrite['avg_f1']:.4f} (±{bge_rewrite.get('std_f1', 0):.4f})"
        )
        print(
            f"  e5-large-v2: F1 = {e5_rewrite['avg_f1']:.4f} (±{e5_rewrite.get('std_f1', 0):.4f})"
        )
        delta_f1 = e5_rewrite["avg_f1"] - bge_rewrite["avg_f1"]
        print(f"  Δ F1:        {delta_f1:+.4f} ({delta_f1 / bge_rewrite['avg_f1'] * 100:+.2f}%)")
        print()
        print(f"  bge-m3:      Retrieval = {bge_rewrite['avg_retrieval_time']:.2f} ms")
        print(f"  e5-large-v2: Retrieval = {e5_rewrite['avg_retrieval_time']:.2f} ms")
        delta_time = e5_rewrite["avg_retrieval_time"] - bge_rewrite["avg_retrieval_time"]
        print(
            f"  Δ Time:      {delta_time:+.2f} ms ({delta_time / bge_rewrite['avg_retrieval_time'] * 100:+.2f}%)"
        )
        print()

    # 总结
    print("【总结】")
    for s in strategies:
        print(f"  {s['name']:50s} | F1: {s['avg_f1']:.4f} | Tasks: {s['task_count']}")
    print()
    print("=" * 80)


def main():
    """主函数"""
    base_dir = Path(".sage/benchmarks/benchmark_memory/locomo")

    strategies = [
        "PreInsert_Mem0g_none",
        "Additional_Mem0g_none_e5_large",
        "PreInsert_Mem0g_rewrite_triplet_extract",
        "Additional_Mem0g_rewrite_e5_large",
    ]

    results = []
    for strategy in strategies:
        print(f"加载 {strategy}...")
        result = analyze_strategy(strategy, base_dir)
        results.append(result)

    print()
    print_comparison(results)


if __name__ == "__main__":
    main()
