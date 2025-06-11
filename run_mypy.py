#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "mypy>=1.16.0",
# ]
# ///
"""
Run mypy on the memgraph package using uv run.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run mypy on the memgraph package."""
    project_dir = Path(__file__).parent

    try:
        # Run mypy on the memgraph package
        result = subprocess.run(
            ["mypy", "memgraph/"],
            cwd=project_dir,
            capture_output=False,  # Let output go to console
            text=True
        )

        return result.returncode

    except FileNotFoundError:
        print("Error: 'mypy' command not found")
        return 1
    except Exception as e:
        print(f"Error running mypy: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
