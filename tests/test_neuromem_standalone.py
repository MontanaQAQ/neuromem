"""
Standalone smoke tests for neuromem package.

These tests validate basic neuromem functionality when installed as a standalone package.
Comprehensive integration tests are maintained in SAGE main repository.

Note: These tests only verify package structure and imports that don't require
SAGE dependencies. Full functionality tests run in SAGE CI.
"""

import os
from pathlib import Path

# Module-level constants for package structure
REQUIRED_SUBMODULES = ["memory_collection", "storage_engine", "utils"]
REQUIRED_PACKAGE_FILES = ["__init__.py", "memory_manager.py"]
REQUIRED_REPO_FILES = ["pyproject.toml", "README.md"]


def get_neuromem_root() -> Path:
    """Get the neuromem root directory.

    Returns:
        Path: The root directory of the neuromem package.

    The path is determined by:
    1. NEUROMEM_ROOT environment variable (used in CI when tests run from /tmp)
    2. Fallback: relative path from this test file's parent directory
    """
    if "NEUROMEM_ROOT" in os.environ:
        return Path(os.environ["NEUROMEM_ROOT"])
    return Path(__file__).parent.parent


def get_package_dir() -> Path:
    """Get the neuromem package directory.

    Returns:
        Path: The directory containing neuromem package source files.
    """
    return get_neuromem_root() / "sage" / "neuromem"


def test_package_structure_exists():
    """Test that neuromem package structure exists."""
    current_dir = get_package_dir()

    for dirname in REQUIRED_SUBMODULES:
        dir_path = current_dir / dirname
        assert dir_path.exists(), f"Required directory {dirname} not found"
        assert dir_path.is_dir(), f"{dirname} is not a directory"


def test_package_files_exist():
    """Test that key package files exist."""
    package_dir = get_package_dir()
    repo_dir = get_neuromem_root()

    for filename in REQUIRED_PACKAGE_FILES:
        file_path = package_dir / filename
        assert file_path.exists(), f"Required package file {filename} not found"

    for filename in REQUIRED_REPO_FILES:
        file_path = repo_dir / filename
        assert file_path.exists(), f"Required file {filename} not found"


def test_submodule_init_files_exist():
    """Test that all submodule __init__.py files exist."""
    current_dir = get_package_dir()

    for submodule in REQUIRED_SUBMODULES:
        init_file = current_dir / submodule / "__init__.py"
        assert init_file.exists(), f"Missing __init__.py in {submodule}"
