#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "mypy",
#     "ruff",
# ]
# ///
"""
Type checking and linting tool for memgraph project
"""

import subprocess
import sys
from pathlib import Path


def run_mypy():
    """Run mypy type checking"""
    print("🔍 Running mypy type checking...")
    result = subprocess.run([
        "mypy",
        "--python-version", "3.12",
        "memgraph/"
    ], cwd=Path(__file__).parent)
    return result.returncode == 0


def run_ruff():
    """Run ruff linting"""
    print("🔍 Running ruff linting...")
    result = subprocess.run([
        "ruff", "check", "memgraph/"
    ], cwd=Path(__file__).parent)
    return result.returncode == 0


def main():
    print("🚀 Running type checking and linting...")

    mypy_ok = run_mypy()
    ruff_ok = run_ruff()

    if mypy_ok and ruff_ok:
        print("✅ All checks passed!")
    else:
        print("❌ Issues found - check output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
