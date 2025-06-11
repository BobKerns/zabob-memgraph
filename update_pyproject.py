#!/usr/bin/env python3
"""
Safely append development tools configuration to pyproject.toml
"""

import toml
from pathlib import Path

def update_pyproject_toml():
    """Safely update pyproject.toml with dev tool configs"""
    pyproject_path = Path("pyproject.toml")
    
    # Read existing content
    if pyproject_path.exists():
        try:
            with open(pyproject_path, 'r') as f:
                existing_config = toml.load(f)
            print("✅ Loaded existing pyproject.toml")
        except Exception as e:
            print(f"❌ Error reading pyproject.toml: {e}")
            return False
    else:
        existing_config = {}
        print("📝 Creating new pyproject.toml")
    
    # Add tool configurations (only if not already present)
    dev_tools_config = {
        "tool": {
            "mypy": {
                "python_version": "3.12",
                "strict": True,
                "warn_return_any": True,
                "warn_unused_configs": True,
                "disallow_untyped_defs": True,
                "disallow_incomplete_defs": True,
                "check_untyped_defs": True,
                "disallow_untyped_decorators": True
            },
            "ruff": {
                "target-version": "py312",
                "line-length": 100
            }
        }
    }
    
    # Add ruff lint configuration
    if "tool" not in existing_config:
        existing_config["tool"] = {}
    
    if "ruff" not in existing_config["tool"]:
        existing_config["tool"]["ruff"] = dev_tools_config["tool"]["ruff"]
        print("✅ Added ruff configuration")
    else:
        print("ℹ️  ruff configuration already exists")
    
    if "mypy" not in existing_config["tool"]:
        existing_config["tool"]["mypy"] = dev_tools_config["tool"]["mypy"]
        print("✅ Added mypy configuration")
    else:
        print("ℹ️  mypy configuration already exists")
    
    # Add ruff lint section if needed
    if "lint" not in existing_config["tool"].get("ruff", {}):
        if "ruff" not in existing_config["tool"]:
            existing_config["tool"]["ruff"] = {}
        
        existing_config["tool"]["ruff"]["lint"] = {
            "select": [
                "E",   # pycodestyle errors
                "W",   # pycodestyle warnings  
                "F",   # pyflakes
                "UP",  # pyupgrade
                "B",   # flake8-bugbear
                "I",   # isort
            ],
            "ignore": [],
            "per-file-ignores": {
                "__init__.py": ["F401"]  # Allow unused imports in __init__.py
            }
        }
        print("✅ Added ruff lint configuration")
    
    # Write back to file
    try:
        with open(pyproject_path, 'w') as f:
            toml.dump(existing_config, f)
        print("✅ Updated pyproject.toml successfully")
        return True
    except Exception as e:
        print(f"❌ Error writing pyproject.toml: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Safely updating pyproject.toml with dev tool configs...")
    update_pyproject_toml()
