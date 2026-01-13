"""Locomo 数据集适配器

包装 sage.data.sources.locomo.dataloader.LocomoDataLoader
"""

from __future__ import annotations

from typing import Any

from benchmarks.experiment.utils.dataloader.base import BaseDataLoader


class LocomoAdapter(BaseDataLoader):
    """Locomo 数据集适配器

    Locomo 是长轮对话记忆数据集，每个 dialog 包含 2 个对话（Q&A）。

    特点:
        - dialog_increment = 2（每次处理一对 Q&A）
        - 支持多 session 结构
    """

    def __init__(self):
        """初始化适配器，延迟加载外部 DataLoader"""
        self._loader = None

    def _ensure_loader(self):
        """确保 loader 已初始化（延迟加载）"""
        if self._loader is None:
            from sage.data.sources.locomo.dataloader import LocomoDataLoader

            self._loader = LocomoDataLoader()

    @property
    def dataset_name(self) -> str:
        return "locomo"

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
        """Locomo 每次处理 2 个对话（Q&A）"""
        return 2
