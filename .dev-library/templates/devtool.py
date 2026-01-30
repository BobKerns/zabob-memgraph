#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.3.1",
#     "gitpython>=3.1.46",
#     "ruff>=0.8.0",
#     "mypy>=1.13.0",
# ]
# ///
"""
Project Development Tool - Template for Zabob projects.

This template shows the simplified pattern for integrating dev-library tools.

Usage:
1. Copy this to your project root as 'devtool'
2. Make executable: chmod +x devtool
3. Adjust CHECK_CONFIG paths for your project structure
4. Add project-specific commands as needed

Standard command structure:
    devtool tools {add,status,push,pull}  - Dev-library management
    devtool {ruff,mypy,check}             - Code quality checks
    devtool <project-specific>            - Your project commands
"""

import sys
from pathlib import Path

# Add .dev-library to path
dev_lib = Path(__file__).parent / ".dev-library"
sys.path.insert(0, str(dev_lib))

from zabob.tools.libtools import cli, CONFIG  # noqa: E402

# Configure default paths for check commands
project_root = Path(__file__).parent
CONFIG["paths"] = [
    project_root / "src",
    project_root / "tests",
    *CONFIG["paths"]
]
CONFIG["config"] = str(project_root / "pyproject.toml")


# Add your project-specific commands here
# Example:
#
# @cli.command()
# def lint():
#     """Run linting checks."""
#     click.echo("Running linters...")
#     # Your lint logic here
#
# @cli.command()
# def test():
#     """Run tests."""
#     click.echo("Running tests...")
#     # Your test logic here
#
# @cli.command()
# def build():
#     """Build the project."""
#     click.echo("Building project...")
#     # Your build logic here


if __name__ == "__main__":
    cli()
