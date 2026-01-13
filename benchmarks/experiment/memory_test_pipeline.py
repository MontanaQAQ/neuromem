"""Locomo 长轮对话记忆实验 - Pipeline 架构

详细架构说明和测试机制请参考: mem_docs/Pipeline_README.md
注意：修改代码时请同步更新该文档
"""

from __future__ import annotations

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service import (
    PipelineBridge,
    PipelineService,
    PipelineServiceSink,
    PipelineServiceSource,
)

from benchmarks.experiment.libs.memory_evaluation import (
    MemoryEvaluation,
)
from benchmarks.experiment.libs.memory_insert import MemoryInsert
from benchmarks.experiment.libs.memory_retrieval import (
    MemoryRetrieval,
)
from benchmarks.experiment.libs.memory_sink import MemorySink
from benchmarks.experiment.libs.memory_source import MemorySource
from benchmarks.experiment.libs.pipeline_caller import (
    PipelineCaller,
)
from benchmarks.experiment.libs.post_insert import PostInsert
from benchmarks.experiment.libs.post_retrieval import PostRetrieval
from benchmarks.experiment.libs.pre_insert import PreInsert
from benchmarks.experiment.libs.pre_retrieval import PreRetrieval
from benchmarks.experiment.utils import RuntimeConfig, parse_args, process_logger
from sage.neuromem.services import NeuromemServiceFactory


def main():
    """主函数"""
    CustomLogger.disable_global_console_debug()

    # 解析命令行参数并加载配置
    args = parse_args()
    config = RuntimeConfig.load(args.config, args.task_id)

    # 初始化过程日志
    dataset = config.get("runtime.dataset", "default")
    task_id = config.get("task_id", "unknown")
    memory_name = config.get("runtime.memory_name", "default")
    process_logger.setup(dataset, memory_name, task_id)

    # 创建环境
    env = LocalEnvironment("memory_test_experiment")

    # 注册服务 - 使用工厂模式动态创建服务
    # 配置格式：
    #   services:
    #     services_type: "partitional.fifo_queue"  # <类型>.<具体实现>
    #     fifo_queue:
    #       max_size: 5

    services_type = config.get("services.services_type")
    if not services_type:
        raise ValueError("Missing required config: services.services_type")

    # 创建 neuromem Service 工厂
    factory = NeuromemServiceFactory.create(services_type, config)

    # 注册名称：从 services_type 中提取具体实现名称
    # "partitional.fifo_queue" -> "fifo_queue"
    registered_name = services_type.split(".")[-1]
    env.register_service_factory(registered_name, factory)

    # 获取服务超时配置（默认 300 秒，足够 link_evolution 等耗时操作）
    pipeline_service_timeout = config.get("runtime.pipeline_service_timeout", 300.0)

    insert_bridge = PipelineBridge()
    env.register_service(
        "memory_insert_service",
        PipelineService,
        insert_bridge,
        request_timeout=pipeline_service_timeout,
    )

    test_bridge = PipelineBridge()
    env.register_service(
        "memory_test_service",
        PipelineService,
        test_bridge,
        request_timeout=pipeline_service_timeout,
    )

    # 创建 Pipeline
    # 记忆插入Pipeline
    (
        env.from_source(PipelineServiceSource, insert_bridge)
        .map(PreInsert, config)
        .map(MemoryInsert, config)
        .map(PostInsert, config)
        .sink(PipelineServiceSink)
    )

    # 记忆测试（包含检索）Pipeline
    (
        env.from_source(PipelineServiceSource, test_bridge)
        .map(PreRetrieval, config)
        .map(MemoryRetrieval, config)
        .map(PostRetrieval, config)
        .map(MemoryEvaluation, config)
        .sink(PipelineServiceSink)
    )

    # 主Pipeline，通过背压机制实现one by one处理
    (env.from_batch(MemorySource, config).map(PipelineCaller, config).sink(MemorySink, config))

    # 启动并等待完成
    env.submit(autostop=True)

    # 关闭过程日志
    process_logger.close()


if __name__ == "__main__":
    main()
