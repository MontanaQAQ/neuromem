"""Path utilities for NeuroMem."""
import os
from pathlib import Path


def get_default_data_dir():
    """Get default data directory following XDG Base Directory Specification.

    Returns:
        str: Absolute path to data directory
    """
    # Try to import SAGE config if available (for backward compatibility)
    try:
        from sage.common.config import find_sage_project_root

        project_root = find_sage_project_root()
        if project_root is not None:
            # If running within SAGE project, use project-local directory
            data_dir = os.path.join(project_root, ".sage", "cache", "neuromem_data")
            os.makedirs(data_dir, exist_ok=True)
            return data_dir
    except (ImportError, FileNotFoundError):
        pass

    # Otherwise, use XDG data directory (standalone mode)
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        data_dir = Path(xdg_data_home) / "neuromem"
    else:
        data_dir = Path.home() / ".local" / "share" / "neuromem"

    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)
