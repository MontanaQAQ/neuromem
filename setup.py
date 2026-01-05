import subprocess
import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def install_precommit_hooks():
    """Install pre-commit hooks if .pre-commit-config.yaml exists."""
    setup_dir = Path(__file__).parent.resolve()
    precommit_config = setup_dir / ".pre-commit-config.yaml"

    # Only install if this is a git repository (file or directory) and has pre-commit config
    git_path = setup_dir / ".git"
    is_git_repo = git_path.exists() and (git_path.is_dir() or git_path.is_file())

    if not is_git_repo or not precommit_config.exists():
        return

    try:
        # Check if pre-commit is already installed
        subprocess.run(
            ["pre-commit", "--version"],
            capture_output=True,
            check=False,
        )

        # Install the hooks
        print("Installing pre-commit hooks for neuromem...")
        result = subprocess.run(
            ["pre-commit", "install"],
            cwd=setup_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print("✅ Pre-commit hooks installed successfully for neuromem")
        else:
            print(
                f"⚠️  Pre-commit hooks installation skipped (exit code {result.returncode})",
                file=sys.stderr,
            )

    except (FileNotFoundError, subprocess.SubprocessError):
        # pre-commit not installed or other error, silently skip
        pass


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        develop.run(self)
        install_precommit_hooks()


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)
        install_precommit_hooks()


with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="neuromem",
    version="0.2.0.1",
    author="IntelliStream Team",
    author_email="your-email@example.com",
    description="Standalone memory management engine for RAG applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/intellistream/neuromem",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "faiss-cpu>=1.7.0",  # 或 faiss-gpu
    ],
    extras_require={
        "bm25s": ["bm25s>=0.1.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "ruff==0.14.2",  # Pin version to match SAGE main repo and CI/CD
            "pre-commit>=3.0.0",
        ],
    },
    cmdclass={
        "develop": PostDevelopCommand,
        "install": PostInstallCommand,
    },
)
