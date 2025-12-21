import os


def get_default_data_dir():
    """获取默认数据目录

    返回项目根目录下的 .sage/cache/neuromem_data，
    确保路径不受当前工作目录影响。

    Returns:
        str: 数据目录的绝对路径
    """
    from sage.common.config import find_sage_project_root

    project_root = find_sage_project_root()
    if project_root is None:
        raise FileNotFoundError("无法找到 SAGE 项目根目录。请确保在 SAGE 项目中运行此代码。")

    data_dir = os.path.join(project_root, ".sage", "cache", "neuromem_data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
