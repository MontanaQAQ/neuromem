"""Embedding 生成工具

提供统一的 embedding 生成接口，支持本地和远程 embedding 服务
"""

import time

from sage.common.components.sage_embedding.embedding_api import apply_embedding_model

# 扩展的 embedding 模型维度映射（补充 sage-common 中未定义的模型）
EXTENDED_EMBEDDING_DIMENSIONS = {
    "intfloat/e5-large-v2": 1024,
    "intfloat/e5-base-v2": 768,
    "intfloat/e5-small-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
}


def _patch_embedding_model_dimensions():
    """在运行时动态补丁 sage-common 的 embedding 模型维度映射

    这样可以在不修改 sage-common 源码的情况下支持新的 embedding 模型。
    """
    try:
        from sage.common.components.sage_embedding.embedding_model import EmbeddingModel

        # 获取原始的 set_dim 方法
        original_set_dim = EmbeddingModel.set_dim

        def patched_set_dim(self, model_name):
            """补丁版本的 set_dim，优先使用扩展的维度映射"""
            # 先检查扩展映射
            if model_name in EXTENDED_EMBEDDING_DIMENSIONS:
                self.dim = EXTENDED_EMBEDDING_DIMENSIONS[model_name]
                return

            # 回退到原始方法
            try:
                original_set_dim(self, model_name)
            except ValueError as err:
                # 如果原始方法也不认识，再抛出错误
                raise ValueError(
                    f"Unknown embedding model: {model_name}. "
                    f"Please add it to EXTENDED_EMBEDDING_DIMENSIONS in "
                    f"benchmarks/experiment/utils/llm/embedding_generator.py"
                ) from err

        # 替换方法
        EmbeddingModel.set_dim = patched_set_dim

    except Exception as e:
        # 补丁失败不影响主流程（对于已知模型）
        print(f"[WARNING] Failed to patch EmbeddingModel dimensions: {e}")


# 在模块加载时自动应用补丁
_patch_embedding_model_dimensions()


class EmbeddingGenerator:
    """Embedding 生成器类"""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str = "BAAI/bge-m3",
        api_key: str = "dummy",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """初始化 Embedding 生成器

        Args:
            base_url: Embedding 服务器地址 (例如 "http://localhost:8091/v1")
                     如果为 None，则不使用 embedding
            model_name: 模型名称
            api_key: API 密钥 (本地服务使用 "dummy")
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
        """
        self.base_url = base_url
        self.model_name = model_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if base_url:
            # 初始化 embedding 模型
            self.embedding_model = apply_embedding_model(
                name="openai",
                model=model_name,
                base_url=base_url,
                api_key=api_key,
            )
        else:
            self.embedding_model = None

    @classmethod
    def from_config(cls, config) -> "EmbeddingGenerator":
        """从配置对象创建 EmbeddingGenerator

        Args:
            config: RuntimeConfig 对象

        Returns:
            EmbeddingGenerator 实例
        """
        base_url = config.get("runtime.embedding_base_url")
        model_name = config.get("runtime.embedding_model", "BAAI/bge-m3")
        max_retries = config.get("runtime.embedding_max_retries", 3)
        retry_delay = config.get("runtime.embedding_retry_delay", 1.0)

        return cls(
            base_url=base_url,
            model_name=model_name,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

    def embed(self, text: str) -> list[float] | None:
        """对单个文本进行 embedding（带重试机制）

        Args:
            text: 输入文本

        Returns:
            embedding 向量，如果未配置 embedding 服务则返回 None
        """
        if self.embedding_model is None:
            return None

        last_error = None
        for attempt in range(self.max_retries):
            try:
                return self.embedding_model.embed(text)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    print(
                        f"[EmbeddingGenerator] Retry {attempt + 1}/{self.max_retries} after error: {e}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))  # 递增延迟

        # 所有重试都失败了
        raise RuntimeError(
            f"Embedding failed after {self.max_retries} retries: {last_error}"
        ) from last_error

    def embed_batch(self, texts: list[str]) -> list[list[float]] | None:
        """对多个文本进行批量 embedding（带重试机制，严格批量）

        严格使用底层模型的原生批量接口，不回退到逐个调用。

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表，如果未配置 embedding 服务则返回 None

        Raises:
            RuntimeError: 批量 embedding 失败
            NotImplementedError: 底层模型不支持批量接口
        """
        if self.embedding_model is None:
            return None

        if not texts:
            return []

        # 严格使用批量接口（带重试）
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return self.embedding_model.embed_batch(texts)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    print(
                        f"[EmbeddingGenerator] Batch retry {attempt + 1}/{self.max_retries} after error: {e}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))

        raise RuntimeError(
            f"Batch embedding failed after {self.max_retries} retries: {last_error}"
        ) from last_error

    def is_available(self) -> bool:
        """检查 embedding 服务是否可用

        Returns:
            True 如果已配置 embedding 服务，否则 False
        """
        return self.embedding_model is not None
