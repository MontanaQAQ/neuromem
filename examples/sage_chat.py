"""基于 STM Pipeline 的聊天机器人

使用独立的 Pipeline 模块处理业务逻辑，本程序专注交互逻辑
"""

from __future__ import annotations

import contextlib

from pipeline.short_term_memory_pipeline import STMPipeline

# ============================================================================
# 配置参数（在此处修改）
# ============================================================================

PIPELINE_CONFIG = {
    # 记忆服务配置
    "service_type": "partitional.fifo_queue",  # 服务类型: partitional.fifo_queue, partitional.lsh_hash, etc.
    "max_size": 10,  # FIFO 队列最大容量（轮次）
    "max_history": 10,  # 检索时返回的最大历史记录数
    # LLM 配置
    "use_llm": True,  # 是否使用真实 LLM（False 则使用模拟回复）
    "api_key": "iloveshuhao",
    "base_url": "http://172.17.0.1:1040/v1",
    "model_name": "pangu_embedded_1b",
    "max_tokens": 256,
    "temperature": 0.7,
}


def main():
    """主函数"""
    print("🚀 启动 NeuroMem STM 聊天机器人...")
    print("━" * 50)
    print("📝 当前配置:")
    print(f"   - 服务类型: {PIPELINE_CONFIG['service_type']}")
    print(f"   - 队列大小: {PIPELINE_CONFIG['max_size']}")
    print(f"   - 检索数量: {PIPELINE_CONFIG['max_history']}")
    print(f"   - 使用 LLM: {PIPELINE_CONFIG['use_llm']}")
    if PIPELINE_CONFIG["use_llm"]:
        print(f"   - 模型名称: {PIPELINE_CONFIG['model_name']}")
    print("━" * 50)

    try:
        # 初始化 Pipeline（注入配置参数）
        pipeline = STMPipeline(config=PIPELINE_CONFIG)
        print("✅ Pipeline 已创建，开始聊天！")
        print("💡 输入 'exit' 或 'quit' 退出聊天\n")

        turn = 0

        while True:
            try:
                # 获取用户输入（阻塞式）
                print(f"💬 [第{turn + 1}轮] 用户: ", end="", flush=True)
                user_input = input().strip()

                # 检查退出命令
                if user_input.lower() in ["exit", "quit", "退出"]:
                    print("👋 再见！")
                    break

                if not user_input:
                    continue

                turn += 1

                # 调用 Pipeline 处理
                result = pipeline.process(user_input, turn)

                # 显示结果
                assistant_reply = result["assistant_reply"]
                retrieval_count = result["retrieval_count"]

                print(f"🤖 [第{turn}轮] 助手: {assistant_reply}")
                print(f"   📊 检索到 {retrieval_count} 条历史记录")

            except KeyboardInterrupt:
                print("\n👋 用户中断，退出聊天。")
                break
            except Exception as e:
                print(f"❌ 处理出错: {e}")
                import traceback

                traceback.print_exc()
                continue

        # 退出前停止 pipeline
        with contextlib.suppress(Exception):
            pipeline.close()

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
