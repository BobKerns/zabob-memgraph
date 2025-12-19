#!/usr/bin/env python3
"""
Syntax checker for the memgraph package.
"""

import ast
import sys
from pathlib import Path


def check_syntax(file_path: Path) -> tuple[bool, str]:
    """Check syntax of a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse the AST to check for syntax errors
        ast.parse(content, filename=str(file_path))
        return True, "OK"

    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def main():
    """Check all Python files in the memgraph package."""
    project_dir = Path(__file__).parent
    memgraph_dir = project_dir / "memgraph"

    if not memgraph_dir.exists():
        print(f"Error: {memgraph_dir} does not exist")
        return 1

    python_files = list(memgraph_dir.rglob("*.py"))

    if not python_files:
        print("No Python files found in memgraph/")
        return 1

    print(f"Checking {len(python_files)} Python files...")

    errors = []
    for file_path in sorted(python_files):
        relative_path = file_path.relative_to(project_dir)
        is_valid, message = check_syntax(file_path)

        if is_valid:
            print(f"✓ {relative_path}")
        else:
            print(f"✗ {relative_path}: {message}")
            errors.append((relative_path, message))

    if errors:
        print(f"\nFound {len(errors)} syntax errors:")
        for file_path, error in errors:
            print(f"  {file_path}: {error}")
        return 1
    else:
        print(f"\nAll {len(python_files)} files have valid syntax!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
