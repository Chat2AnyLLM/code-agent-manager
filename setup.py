"""Setup configuration for Code Assistant Manager."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""


def read_version():
    import re
    from pathlib import Path

    init_py = Path(__file__).parent / "code_assistant_manager" / "__init__.py"
    text = init_py.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+) ["\']', text, re.M)
    return m.group(1) if m else "0.0.0"

setup(
    name="code-assistant-manager",
    version=read_version(),
    description="CLI utilities for working with AI coding assistants",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Code Assistant Manager Contributors",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "PyYAML>=6.0.1",
        "python-dotenv>=1.0.1",
        "typer>=0.12.0",
        "click>=8.1.7",
        "rich>=13.7.0",
        "pydantic>=2.6.0",
        "typing-extensions>=4.10.0",
        "httpx>=0.27.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.23.0",
            "psutil>=5.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "code-assistant-manager=code_assistant_manager.cli:main",
            "cam=code_assistant_manager.cli:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)