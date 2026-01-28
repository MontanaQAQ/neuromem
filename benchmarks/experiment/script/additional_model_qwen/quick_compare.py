#!/usr/bin/env python3
"""
快速对比分析：PanGu vs Qwen (D2 Normalization)

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
    print("补充实验：LLM 模型对比分析 (D2 Normalization)")
    print("=" * 80)
    print()

    # 提取对比组
    pangu_none = next((s for s in strategies if "PreInsert_Mem0g_none" in s["name"]), None)
    pangu_rewrite = next((s for s in strategies if "PreInsert_Mem0g_rewrite" in s["name"]), None)
    qwen_none = next((s for s in strategies if "Additional_Qwen_Mem0g_none" in s["name"]), None)
    qwen_rewrite = next(
        (s for s in strategies if "Additional_Qwen_Mem0g_rewrite" in s["name"]), None
    )

    # PanGu 组
    print("【PanGu-1B 组】")
    print("-" * 80)
    if pangu_none:
        print("  Mem0g + None:")
        print(
            f"    • 平均 F1 分数:   {pangu_none['avg_f1']:.4f} (±{pangu_none.get('std_f1', 0):.4f})"
        )
        print(f"    • 平均检索时间:   {pangu_none['avg_retrieval_time']:.2f} ms")
    if pangu_rewrite:
        print("  Mem0g + Rewrite:")
        print(
            f"    • 平均 F1 分数:   {pangu_rewrite['avg_f1']:.4f} (±{pangu_rewrite.get('std_f1', 0):.4f})"
        )
        print(f"    • 平均检索时间:   {pangu_rewrite['avg_retrieval_time']:.2f} ms")

    if pangu_none and pangu_rewrite:
        f1_diff = pangu_rewrite["avg_f1"] - pangu_none["avg_f1"]
        print(f"  → F1 提升: {f1_diff:+.4f} ({f1_diff / pangu_none['avg_f1'] * 100:+.1f}%)")
    print()

    # Qwen 组
    print("【Qwen-Plus 组】")
    print("-" * 80)
    if qwen_none:
        print("  Mem0g + None:")
        print(
            f"    • 平均 F1 分数:   {qwen_none['avg_f1']:.4f} (±{qwen_none.get('std_f1', 0):.4f})"
        )
        print(f"    • 平均检索时间:   {qwen_none['avg_retrieval_time']:.2f} ms")
    if qwen_rewrite:
        print("  Mem0g + Rewrite:")
        print(
            f"    • 平均 F1 分数:   {qwen_rewrite['avg_f1']:.4f} (±{qwen_rewrite.get('std_f1', 0):.4f})"
        )
        print(f"    • 平均检索时间:   {qwen_rewrite['avg_retrieval_time']:.2f} ms")

    if qwen_none and qwen_rewrite:
        f1_diff = qwen_rewrite["avg_f1"] - qwen_none["avg_f1"]
        print(f"  → F1 提升: {f1_diff:+.4f} ({f1_diff / qwen_none['avg_f1'] * 100:+.1f}%)")
    print()

    # LLM 模型对比
    print("【LLM 模型对比】")
    print("-" * 80)
    if pangu_none and qwen_none:
        f1_diff = qwen_none["avg_f1"] - pangu_none["avg_f1"]
        print("  None 策略:")
        print(
            f"    • Qwen vs PanGu F1 差异: {f1_diff:+.4f} ({f1_diff / pangu_none['avg_f1'] * 100:+.1f}%)"
        )

    if pangu_rewrite and qwen_rewrite:
        f1_diff = qwen_rewrite["avg_f1"] - pangu_rewrite["avg_f1"]
        print("  Rewrite 策略:")
        print(
            f"    • Qwen vs PanGu F1 差异: {f1_diff:+.4f} ({f1_diff / pangu_rewrite['avg_f1'] * 100:+.1f}%)"
        )
    print()

    print("=" * 80)


def main():
    base_dir = Path(".sage/benchmarks/benchmark_memory/locomo")

    strategies = [
        "PreInsert_Mem0g_none",
        "PreInsert_Mem0g_rewrite_triplet_extract",
        "Additional_Qwen_Mem0g_none",
        "Additional_Qwen_Mem0g_rewrite",
    ]

    results = []
    for strategy in strategies:
        result = analyze_strategy(strategy, base_dir)
        if result["f1_scores"]:
            results.append(result)

    if not results:
        print("错误: 未找到实验结果")
        print(f"请确保以下目录存在实验数据: {base_dir.absolute()}")
        return

    print_comparison(results)


if __name__ == "__main__":
    main()
