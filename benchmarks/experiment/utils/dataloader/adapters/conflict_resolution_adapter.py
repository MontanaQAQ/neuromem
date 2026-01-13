"""ConflictResolution 数据集适配器

包装 sage.data.sources.memagentbench.conflict_resolution_loader 系列
支持 V1、V2 等多个版本
"""

from __future__ import annotations

from typing import Any

from benchmarks.experiment.utils.dataloader.base import BaseDataLoader


class ConflictResolutionAdapter(BaseDataLoader):
    """ConflictResolution 数据集适配器

    ConflictResolution 是 MemAgentBench 的冲突解决数据集。

    特点:
        - dialog_increment = 1（每次处理 1 个事实）
        - 支持多版本: v1, v2
    """

    def __init__(self, version: str | None = None):
        """初始化适配器

        Args:
            version: 版本标识，可选值：None（默认）, "v1", "v2"
        """
        self._loader = None
        self._version = version

    def _ensure_loader(self):
        """确保 loader 已初始化（延迟加载）"""
        if self._loader is None:
            if self._version == "v1":
                from sage.data.sources.memagentbench.conflict_resolution_loader_v1 import (
                    ConflictResolutionDataLoaderV1,
                )

                self._loader = ConflictResolutionDataLoaderV1()
            elif self._version == "v2":
                from sage.data.sources.memagentbench.conflict_resolution_loader_v2 import (
                    ConflictResolutionDataLoaderV2,
                )

                self._loader = ConflictResolutionDataLoaderV2()
            else:
                from sage.data.sources.memagentbench.conflict_resolution_loader import (
                    ConflictResolutionDataLoader,
                )

                self._loader = ConflictResolutionDataLoader()

    @property
    def dataset_name(self) -> str:
        if self._version:
            return f"conflict_resolution_{self._version}"
        return "conflict_resolution"

    def get_turn(self, task_id: str) -> list[tuple[int, int]]:
        self._ensure_loader()
        return self._loader.get_turn(task_id)

    def get_dialog(self, task_id: str, session_x: int, dialog_y: int) -> list[dict[str, Any]]:
        self._ensure_loader()
        return self._loader.get_dialog(task_id, session_x=session_x, dialog_y=dialog_y)

    def get_total_valid_questions(self, task_id: str) -> int:
        self._ensure_loader()
        return self._loader.get_total_valid_questions(task_id)

    def get_question_list(
        self, task_id: str, session_x: int, dialog_y: int
    ) -> list[dict[str, Any]]:
        self._ensure_loader()
        return self._loader.get_question_list(task_id, session_x, dialog_y)

    def get_dataset_statistics(self, task_id: str) -> dict[str, Any]:
        self._ensure_loader()
        return self._loader.get_dataset_statistics(task_id)

    def get_dialog_increment(self) -> int:
        """ConflictResolution 每次处理 1 个事实"""
        return 1

    def get_packet_count(self, max_dialog_idx: int) -> int:
        """ConflictResolution 每个事实就是一个包"""
        return max_dialog_idx + 1
