"""LongMemEval 数据集适配器

包装 sage.data.sources.longmemeval.LongMemEvalDataLoader
"""

from __future__ import annotations

from typing import Any

from benchmarks.experiment.utils.dataloader.base import BaseDataLoader


class LongMemEvalAdapter(BaseDataLoader):
    """LongMemEval 数据集适配器

    LongMemEval 是长期记忆评估数据集。
    """

    def __init__(self):
        """初始化适配器，延迟加载外部 DataLoader"""
        self._loader = None

    def _ensure_loader(self):
        """确保 loader 已初始化（延迟加载）"""
        if self._loader is None:
            from sage.data.sources.longmemeval import LongMemEvalDataLoader

            self._loader = LongMemEvalDataLoader()

    @property
    def dataset_name(self) -> str:
        return "longmemeval"

    def get_dialog(self, task_id: str, session_x: int, dialog_y: int) -> list[dict[str, Any]]:
        self._ensure_loader()
        return self._loader.get_dialog(task_id, session_x=session_x, dialog_y=dialog_y)

    def get_evaluation(self, task_id: str, session_x: int, dialog_y: int) -> list[dict[str, Any]]:
        self._ensure_loader()
        return self._loader.get_evaluation(task_id, session_x, dialog_y)

    def sessions(self, task_id: str) -> list[tuple[int, int]]:
        self._ensure_loader()
        return self._loader.sessions(task_id)

    def question_count(self, task_id: str) -> int:
        self._ensure_loader()
        return self._loader.question_count(task_id)

    def dialog_count(self, task_id: str) -> int:
        self._ensure_loader()
        return self._loader.dialog_count(task_id)

    def message_count(self, task_id: str) -> int:
        self._ensure_loader()
        return self._loader.message_count(task_id)

    def statistics(self, task_id: str) -> dict[str, Any]:
        self._ensure_loader()
        return self._loader.statistics(task_id)
