from pathlib import Path


def get_project_root() -> Path:
    """
    获取 NeuroMem 项目根目录（包含 pyproject.toml 的目录）

    Returns:
        Path: 项目根目录路径

    Raises:
        FileNotFoundError: 如果未找到项目根目录
    """
    # 从当前文件向上查找，直到找到包含 pyproject.toml 的目录
    current_path = Path(__file__).resolve()

    # 向上遍历目录
    for parent in [current_path] + list(current_path.parents):
        # 检查是否存在项目标识文件
        if (parent / "pyproject.toml").exists():
            return parent

    raise FileNotFoundError("未找到 NeuroMem 项目根目录")
