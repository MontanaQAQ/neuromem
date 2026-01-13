"""数据集加载器抽象基类

定义所有数据集加载器必须实现的统一接口。

接口说明：
- get_turn: 获取任务的所有轮次信息
- get_dialog: 获取指定对话内容
- get_total_valid_questions: 获取有效问题总数
- get_question_list: 获取当前可见的问题列表
- get_dataset_statistics: 获取数据集统计信息
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDataLoader(ABC):
    """统一的数据集加载器抽象基类

    所有数据集适配器必须继承此类并实现全部抽象方法。

    Attributes:
        dataset_name: 数据集名称标识
    """

    @property
    @abstractmethod
    def dataset_name(self) -> str:
        """返回数据集名称标识

        Returns:
            数据集名称，如 "locomo", "longmemeval", "conflict_resolution"
        """

    @abstractmethod
    def get_turn(self, task_id: str) -> list[tuple[int, int]]:
        """获取任务的所有轮次信息

        返回该任务包含的所有 session 及其最大 dialog 索引。

        Args:
            task_id: 任务标识，如 "conv-26"

        Returns:
            轮次列表，每项为 (session_id, max_dialog_idx) 的元组
            例如: [(0, 10), (1, 8), (2, 15)] 表示 3 个 session
        """

    @abstractmethod
    def get_dialog(self, task_id: str, session_x: int, dialog_y: int) -> list[dict[str, Any]]:
        """获取指定对话内容

        根据 session 和 dialog 索引获取具体的对话内容。

        Args:
            task_id: 任务标识
            session_x: session 索引
            dialog_y: dialog 起始索引

        Returns:
            对话列表，每项为包含 speaker 和 text 的字典
            例如: [{"speaker": "user", "text": "Hello"}, {"speaker": "assistant", "text": "Hi"}]
        """

    @abstractmethod
    def get_total_valid_questions(self, task_id: str) -> int:
        """获取任务的有效问题总数

        用于计算测试阈值和进度统计。

        Args:
            task_id: 任务标识

        Returns:
            有效问题总数
        """

    @abstractmethod
    def get_question_list(
        self, task_id: str, session_x: int, dialog_y: int
    ) -> list[dict[str, Any]]:
        """获取当前可见的问题列表

        返回在指定 session/dialog 位置时可见的问题。

        Args:
            task_id: 任务标识
            session_x: session 索引
            dialog_y: dialog 索引

        Returns:
            问题列表，每项为问题字典（具体格式因数据集而异）
        """

    @abstractmethod
    def get_dataset_statistics(self, task_id: str) -> dict[str, Any]:
        """获取数据集统计信息

        用于结果保存时记录数据集元信息。

        Args:
            task_id: 任务标识

        Returns:
            统计信息字典，包含数据集相关的统计数据
        """

    # ========== 可选方法（子类可覆盖）==========

    def get_dialog_increment(self) -> int:
        """获取 dialog 指针的增量

        不同数据集的对话结构不同：
        - locomo/longmemeval: 每包含 2 个对话（Q&A），增量为 2
        - conflict_resolution: 每包含 1 个事实，增量为 1

        Returns:
            dialog 指针每次移动的增量，默认为 2
        """
        return 2

    def get_packet_count(self, max_dialog_idx: int) -> int:
        """计算 session 的数据包数量

        根据 max_dialog_idx 和增量计算该 session 需要发送的数据包数。

        Args:
            max_dialog_idx: session 的最大 dialog 索引

        Returns:
            数据包数量
        """
        increment = self.get_dialog_increment()
        return (max_dialog_idx // increment) + 1
