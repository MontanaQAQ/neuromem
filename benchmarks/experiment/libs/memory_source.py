"""记忆实验数据源 - 支持多数据集的统一接口

详细文档请参考: mem_docs/MemorySource.md
注意：修改代码时请同步更新该文档
"""

from sage.common.core import BatchFunction

from benchmarks.experiment.utils.dataloader import DataLoaderFactory


class MemorySource(BatchFunction):
    """
    从多种数据集中逐个读取对话轮次的Source

    详细说明（支持的数据集、输出格式、配置方法等）请参考:
    mem_docs/MemorySource.md
    """

    def __init__(self, config):
        """初始化数据源

        初始化流程：
        1. 检查数据集和task_id合理性
        2. 创建数据加载器并获取数据集核心信息
        3. 打印当前任务信息
        4. 初始化任务指针

        Args:
            config: RuntimeConfig 对象，从中获取 dataset 和 task_id
        """
        super().__init__()
        self.dataset = config.get("dataset")
        self.task_id = config.get("task_id")

        # Create data loader (使用工厂模式)
        self.loader = DataLoaderFactory.create(self.dataset)

        # 获取数据集核心信息
        self.turns = self.loader.get_turn(self.task_id)

        # 统计总的dialog数量和数据包数量
        self.total_dialogs = sum((max_dialog_idx + 1) for _, max_dialog_idx in self.turns)

        # 使用 loader 的方法计算数据包数量（不同数据集增量不同）
        self.total_packets = sum(
            self.loader.get_packet_count(max_dialog_idx) for _, max_dialog_idx in self.turns
        )

        # 获取 dialog 增量（用于后续指针移动）
        self.dialog_increment = self.loader.get_dialog_increment()

        # 打印当前任务信息
        print(f"📊 样本 {self.task_id} 统计信息:")
        print(f"   - 总会话数: {len(self.turns)}")
        print(f"   - 总对话数: {self.total_dialogs}")
        print(f"   - 总数据包: {self.total_packets}")
        for idx, (session_id, max_dialog_idx) in enumerate(self.turns):
            dialog_count = max_dialog_idx + 1
            print(
                f"   - 会话 {idx + 1} (session_id={session_id}): {dialog_count} 个对话 (max_dialog_idx={max_dialog_idx})"
            )

        # 初始化任务指针
        self.session_idx = 0  # 当前session在turns列表中的索引
        self.dialog_ptr = 0  # 当前dialog指针（偶数）
        self.packet_idx = 0  # 当前数据包序号（从0开始）

    def execute(self):
        """执行数据读取

        注意：BatchFunction 的 execute() 会被循环调用，每次返回一个数据项
        当返回 None 时，表示数据源耗尽，会触发停止信号
        """
        import time

        # 【背压控制】添加小延迟，避免数据源产生过快
        time.sleep(0.01)  # 10ms延迟，可根据实际情况调整

        # 检查是否已经遍历完所有session
        if self.session_idx >= len(self.turns):
            print(f"🏁 MemorySource 已完成：所有 {len(self.turns)} 个会话已处理完毕")
            return None

        # Get current session info
        session_id, max_dialog_idx = self.turns[self.session_idx]

        # Check if current session is complete
        if self.dialog_ptr > max_dialog_idx:
            # Move to next session
            self.session_idx += 1
            self.dialog_ptr = 0

            # Check if there are more sessions
            if self.session_idx >= len(self.turns):
                return None

            # Update to new session info
            session_id, max_dialog_idx = self.turns[self.session_idx]

        # Get current dialog
        dialogs = self.loader.get_dialog(
            self.task_id, session_x=session_id, dialog_y=self.dialog_ptr
        )

        # 计算下一个 dialog_ptr (用于判断是否为 session 最后一个包)
        next_dialog_ptr = self.dialog_ptr + self.dialog_increment

        # 判断是否为当前 session 的最后一个数据包
        is_session_end = next_dialog_ptr > max_dialog_idx

        # Prepare return data (with sequence information)
        result = {
            "task_id": self.task_id,
            "session_id": session_id,
            "dialog_id": self.dialog_ptr,
            "dialogs": dialogs,
            "dialog_len": len(dialogs),
            "packet_idx": self.packet_idx,  # Current packet index (from 0)
            "total_packets": self.total_packets,  # Total packets
            "is_session_end": is_session_end,  # 是否为当前 session 的最后一个包
        }

        # 移动指针到下一个 dialog（使用 loader 定义的增量）
        self.dialog_ptr += self.dialog_increment

        self.packet_idx += 1  # Packet index increment

        return result
