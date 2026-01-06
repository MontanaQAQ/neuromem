import json
import os

from sage.common.core import SinkFunction

from benchmarks.experiment.utils import (
    get_project_root,
    get_runtime_timestamp,
    get_time_filename,
)


class MemorySink(SinkFunction):
    """收集测试结果并保存为 JSON 格式的 Sink"""

    def __init__(self, config):
        """初始化 MemorySink

        Args:
            config: RuntimeConfig 对象，从中获取 dataset 和 task_id
        """
        self.dataset = config.get("dataset")
        self.task_id = config.get("task_id")
        self.test_segments = config.get("runtime.test_segments", 10)
        self.memory_name = config.get("runtime.memory_name", "default")

        # 获取项目根目录
        project_root = get_project_root()

        # 创建时间戳目录结构，包含 memory_name
        time_str = get_time_filename()
        self.output_dir = os.path.join(
            project_root,
            f".sage/benchmarks/benchmark_memory/{self.dataset}/{time_str}/{self.memory_name}",
        )
        os.makedirs(self.output_dir, exist_ok=True)

        # 设置输出文件路径（格式：task_id_HHMM.json）
        runtime_stamp = get_runtime_timestamp()
        self.output_file = os.path.join(self.output_dir, f"{self.task_id}_{runtime_stamp}.json")
        print(f"💾 输出文件: {self.output_file}")

        # 收集所有测试结果
        self.test_results = []

        # 分离存储两种 timing 数据
        self.all_insert_timings = []  # 插入阶段：每个 dialog 的 timing（214条）
        self.all_test_timings = []  # 检索阶段：每次测试的 timing（10次测试）

        # 收集记忆体统计数据（每次测试一条）
        self.all_memory_stats = []

        # 初始化 DataLoader（用于获取统计信息）
        self.loader = self._init_loader(self.dataset)

    def _init_loader(self, dataset):
        """根据数据集类型初始化 DataLoader

        Args:
            dataset: 数据集名称

        Returns:
            DataLoader 实例
        """
        if dataset == "locomo":
            from sage.data.sources.locomo.dataloader import LocomoDataLoader

            return LocomoDataLoader()
        elif dataset == "conflict_resolution":
            from sage.data.sources.memagentbench.conflict_resolution_loader import (
                ConflictResolutionDataLoader,
            )

            return ConflictResolutionDataLoader()
        elif dataset == "conflict_resolution_v1":
            from sage.data.sources.memagentbench.conflict_resolution_loader_v1 import (
                ConflictResolutionDataLoaderV1,
            )

            return ConflictResolutionDataLoaderV1()
        elif dataset == "conflict_resolution_v2":
            from sage.data.sources.memagentbench.conflict_resolution_loader_v2 import (
                ConflictResolutionDataLoaderV2,
            )

            return ConflictResolutionDataLoaderV2()
        elif dataset == "longmemeval":
            from sage.data.sources.longmemeval import LongMemEvalDataLoader

            return LongMemEvalDataLoader()
        else:
            raise ValueError(f"不支持的数据集: {dataset}")

    def execute(self, data):
        """接收并处理测试结果

        Args:
            data: 来自 PipelineCaller 的纯数据字典
                - None: 未触发测试
                - dict: 测试结果或完成信号
                    - completed: True 表示最后一个包
                    - question_range, answers: 测试数据
        """
        if not data:
            # None 表示未触发测试，直接返回
            return

        # 检查是否包含测试结果或 timing 数据
        # 注意：最后一个包可能同时有 completed=True 和 stage_timings（剩余数据）
        if "answers" in data or "stage_timings" in data:
            # 如果有 answers，收集测试结果
            if "answers" in data:
                test_result = {
                    "test_index": len(self.test_results) + 1,
                    "question_range": data.get("question_range"),
                    "dialogs_inserted_count": data.get("dialogs_inserted"),
                    "answers": data.get("answers", []),
                }
                self.test_results.append(test_result)

            # 收集时间数据（无论是否有 answers）
            if "stage_timings" in data:
                stage_timings = data["stage_timings"]
                print(f"[DEBUG MemorySink] stage_timings keys: {stage_timings.keys()}")

                # 收集插入阶段的时间（插入阶段的值是列表，需要展开后合并）
                if "insert" in stage_timings:
                    insert_timing = stage_timings["insert"]
                    print(f"[DEBUG MemorySink] insert_timing type: {type(insert_timing)}")
                    print(
                        f"[DEBUG MemorySink] insert_timing keys: {insert_timing.keys() if isinstance(insert_timing, dict) else 'not a dict'}"
                    )
                    if isinstance(insert_timing, dict) and insert_timing:
                        first_key = next(iter(insert_timing.keys()))
                        first_value = insert_timing[first_key]
                        print(
                            f"[DEBUG MemorySink] first_key={first_key}, value type={type(first_value)}, is_list={isinstance(first_value, list)}"
                        )
                        if isinstance(first_value, list):
                            print(f"[DEBUG MemorySink] list length={len(first_value)}")

                    # 将插入阶段的列表格式数据展开为单独的timing记录
                    # insert_timing = {"pre_insert_ms": [0.01, 0.01], "memory_insert_ms": [3.2, 3.5], ...}
                    # 需要转换为: [{"pre_insert_ms": 0.01, "memory_insert_ms": 3.2, ...}, ...]
                    if insert_timing:
                        # 获取列表长度（所有字段的列表长度应该相同）
                        first_key = next(iter(insert_timing.keys()))
                        if isinstance(insert_timing[first_key], list):
                            list_len = len(insert_timing[first_key])
                            # 转置：将字典的列表值转换为列表的字典值
                            for i in range(list_len):
                                single_timing = {k: v[i] for k, v in insert_timing.items()}
                                self.all_insert_timings.append(single_timing)
                            print(f"[DEBUG MemorySink] Expanded {list_len} insert timings")
                        else:
                            # 如果不是列表格式，直接添加（向后兼容）
                            self.all_insert_timings.append(insert_timing)
                            print("[DEBUG MemorySink] Added 1 insert timing (not list format)")

                # 收集测试阶段的时间（现在是每次测试的平均值字典）
                if "test" in stage_timings:
                    test_timing = stage_timings["test"]
                    if test_timing:  # 非空字典
                        # test_timing 是一个字典，包含本次测试的平均值
                        # {"pre_retrieval_ms": 0.03, "memory_retrieval_ms": 3.5, ...}
                        self.all_test_timings.append(test_timing)
                        print(
                            "[DEBUG MemorySink] Added 1 test timing (average of multiple questions)"
                        )

            # 收集记忆体统计数据（现在在 stage_timings 内部）
            if "stage_timings" in data and "memory_stats" in data["stage_timings"]:
                memory_stats = data["stage_timings"]["memory_stats"]
                if memory_stats:
                    self.all_memory_stats.append(memory_stats)
                    print("[DEBUG MemorySink] Added 1 memory_stats")

        # 检查是否完成
        print(
            f"\n[DEBUG MemorySink] 收到数据: completed={data.get('completed')}, keys={list(data.keys())}"
        )
        if data.get("completed", False):
            print("[DEBUG MemorySink] completed=True，调用 _save_results")
            self._save_results(data)
        else:
            print("[DEBUG MemorySink] completed=False，不保存")

    def _save_results(self, data):
        """保存最终结果

        Args:
            data: 包含 dataset 和 task_id 的数据
        """
        dataset = data.get("dataset", self.dataset)
        task_id = data.get("task_id", self.task_id)

        # 从 DataLoader 获取数据集统计信息
        dataset_stats = self.loader.get_dataset_statistics(task_id)

        # 构造新的 timing_summary 格式
        timing_summary = {
            "insert_timings": self._format_insert_timings(),  # pre_insert, memory_insert, post_insert 的详细统计
            "retrieval_timings": self._format_retrieval_timings(),  # pre_retrieval, memory_retrieval, post_retrieval 的详细统计
        }

        # 格式化 memory_snapshots（按 test_index 组织）
        memory_snapshots = self._format_memory_snapshots()

        # 构造输出 JSON 结构
        output_data = {
            "experiment_info": {
                "dataset": dataset,
                "task_id": task_id,
            },
            "dataset_statistics": dataset_stats,
            "test_summary": {
                "total_tests": len(self.test_results),
                "test_segments": self.test_segments,
                "test_threshold": f"1/{self.test_segments} of total questions",
            },
            "test_results": self._format_test_results(self.test_results),
            "timing_summary": timing_summary,
            "memory_snapshots": memory_snapshots,
        }

        # 保存为 JSON
        print(f"[DEBUG MemorySink] 准备保存到: {self.output_file}")
        print(f"[DEBUG MemorySink] test_results 数量: {len(self.test_results)}")
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"\n✅ 测试结果已保存至: {self.output_file}")
        except Exception as e:
            print(f"[DEBUG MemorySink] 保存失败: {e}")
            import traceback

            traceback.print_exc()

    def _format_test_results(self, test_results):
        """格式化测试结果为通用格式

        Args:
            test_results: 测试结果列表

        Returns:
            list: 格式化后的测试结果
        """
        formatted_results = []

        for test in test_results:
            formatted_test = {
                "test_index": test.get("test_index"),
                "question_range": test.get("question_range"),
                "dialogs_inserted_count": test.get("dialogs_inserted_count"),
                "questions": [],
            }

            # 格式化每个问题的答案
            for answer in test.get("answers", []):
                metadata = answer.get("metadata", {})

                question_data = {
                    "question_index": answer.get("question_index"),
                    "question_text": answer.get("question"),
                    "predicted_answer": answer.get("predicted_answer"),
                }

                # 添加参考答案（如果存在）
                if "answer" in metadata:
                    question_data["reference_answer"] = metadata["answer"]

                # 添加证据信息（如果存在）
                if "evidence" in metadata:
                    question_data["evidence"] = metadata["evidence"]

                # 添加分类信息（如果存在）
                if "category" in metadata:
                    question_data["category"] = metadata["category"]

                # 添加错误信息（如果存在）
                if "error" in answer:
                    question_data["error"] = answer["error"]

                formatted_test["questions"].append(question_data)

            formatted_results.append(formatted_test)

        return formatted_results

    def _format_insert_timings(self) -> dict:
        """格式化插入阶段的 timing 统计

        Returns:
            dict: 包含总统计和每条记录的详细统计
            {
                "summary": {
                    "pre_insert_ms": {"avg": ..., "min": ..., "max": ..., "count": 214},
                    "memory_insert_ms": {...},
                    "post_insert_ms": {...}
                },
                "details": [
                    {"pre_insert_ms": 0.01, "memory_insert_ms": 3.2, "post_insert_ms": 0.02},
                    ...  # 214条记录
                ]
            }
        """
        if not self.all_insert_timings:
            return {"summary": {}, "details": []}

        # 计算总统计
        summary = {}
        stage_names = ["pre_insert_ms", "memory_insert_ms", "post_insert_ms"]

        for stage_name in stage_names:
            values = [timing.get(stage_name, 0) for timing in self.all_insert_timings]
            if values:
                summary[stage_name] = {
                    "avg_ms": sum(values) / len(values),
                    "min_ms": min(values),
                    "max_ms": max(values),
                    "count": len(values),
                }

        return {
            "summary": summary,
            "details": self.all_insert_timings,  # 214条记录
        }

    def _format_retrieval_timings(self) -> dict:
        """格式化检索阶段的 timing 统计

        Returns:
            dict: 包含总统计和每次测试的详细统计
            {
                "summary": {
                    "pre_retrieval_ms": {"avg": ..., "min": ..., "max": ..., "count": 10},
                    "memory_retrieval_ms": {...},
                    "post_retrieval_ms": {...}
                },
                "details": [
                    {"test_index": 1, "pre_retrieval_ms": 0.03, "memory_retrieval_ms": 4.2, "post_retrieval_ms": 0.18},
                    ...  # 10条记录
                ]
            }
        """
        if not self.all_test_timings:
            return {"summary": {}, "details": []}

        # 计算总统计
        summary = {}
        stage_names = ["pre_retrieval_ms", "memory_retrieval_ms", "post_retrieval_ms"]

        for stage_name in stage_names:
            values = [timing.get(stage_name, 0) for timing in self.all_test_timings]
            if values:
                summary[stage_name] = {
                    "avg_ms": sum(values) / len(values),
                    "min_ms": min(values),
                    "max_ms": max(values),
                    "count": len(values),
                }

        # 格式化详细记录（添加 test_index）
        details = []
        for idx, timing in enumerate(self.all_test_timings, start=1):
            detail = {"test_index": idx}
            detail.update(timing)
            details.append(detail)

        return {
            "summary": summary,
            "details": details,  # 10条记录
        }

    def _format_memory_snapshots(self) -> list[dict]:
        """格式化内存快照（按 test_index 组织）

        Returns:
            list: 每次测试的内存快照
            [
                {"test_index": 1, "memory_count": 5, "max_capacity": 5, ...},
                ...  # 10条记录
            ]
        """
        if not self.all_memory_stats:
            return []

        snapshots = []
        for idx, stats in enumerate(self.all_memory_stats, start=1):
            snapshot = {"test_index": idx}
            snapshot.update(stats)
            snapshots.append(snapshot)

        return snapshots
