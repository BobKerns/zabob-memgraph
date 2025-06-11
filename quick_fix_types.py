#!/usr/bin/env python3
"""
Simple type annotation fixer using grep-like approach
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=Path(__file__).parent)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def find_and_replace_in_files(pattern, replacement, file_pattern="*.py"):
    """Find and replace pattern in all Python files"""
    # Use find to get Python files, excluding common directories to avoid
    find_cmd = f"find . -name '{file_pattern}' -not -path './.git/*' -not -path './__pycache__/*' -not -path './.venv/*' -not -path './venv/*' -not -path './env/*' -not -path './.env/*'"
    stdout, stderr, code = run_command(find_cmd)
    
    if code != 0:
        print(f"Error finding files: {stderr}")
        return 0
    
    files = [f.strip() for f in stdout.split('\n') if f.strip()]
    changes = 0
    
    for file_path in files:
        # Use sed to replace in each file
        sed_cmd = f"sed -i.bak 's/{pattern}/{replacement}/g' '{file_path}'"
        _, stderr, code = run_command(sed_cmd)
        
        if code == 0:
            # Check if file changed
            diff_cmd = f"diff '{file_path}.bak' '{file_path}'"
            _, _, diff_code = run_command(diff_cmd)
            
            if diff_code != 0:  # Files differ, change was made
                changes += 1
                print(f"  ✅ Updated {file_path}")
            
            # Clean up backup
            run_command(f"rm '{file_path}.bak'")
        else:
            print(f"  ❌ Error updating {file_path}: {stderr}")
    
    return changes

def main():
    print("🔧 Systematic Type Annotation Fixer")
    print("=" * 40)
    
    # Safety check - make sure we're in the right directory and not in a venv
    current_dir = Path.cwd()
    if '.venv' in str(current_dir) or 'venv' in str(current_dir) or 'site-packages' in str(current_dir):
        print("❌ Error: Running from within a virtual environment!")
        print("   Please run from the project root directory.")
        sys.exit(1)
    
    # List files that will be modified
    find_cmd = "find . -name '*.py' -not -path './.git/*' -not -path './__pycache__/*' -not -path './.venv/*' -not -path './venv/*' -not -path './env/*' -not -path './.env/*'"
    stdout, stderr, code = run_command(find_cmd)
    
    if code != 0:
        print(f"❌ Error finding Python files: {stderr}")
        sys.exit(1)
    
    files = [f.strip() for f in stdout.split('\n') if f.strip()]
    print(f"📁 Found {len(files)} Python files to process:")
    for f in files[:5]:  # Show first 5
        print(f"   {f}")
    if len(files) > 5:
        print(f"   ... and {len(files) - 5} more")
    
    input("\n⚠️  Press Enter to continue or Ctrl+C to abort...")
    
    # Define replacement patterns
    patterns = [
        ("Dict\\[", "dict["),
        ("List\\[", "list["),
        ("Tuple\\[", "tuple["),
        ("Set\\[", "set["),
        ("Optional\\[", "| None  # TODO: Fix | None  # TODO: Fix Optional["),
        ("from typing import Any  # TODO: Clean up imports", "from typing import Any  # TODO: Clean up imports"),
    ]
    
    total_changes = 0
    
    for pattern, replacement in patterns:
        print(f"\n🔍 Replacing '{pattern}' with '{replacement}'...")
        changes = find_and_replace_in_files(pattern, replacement)
        total_changes += changes
        print(f"   Made {changes} changes")
    
    print(f"\n🎉 Total files changed: {total_changes}")
    
    if total_changes > 0:
        print("\n📝 Manual cleanup needed:")
        print("   - Fix | None  # TODO: Fix Optional[] replacements")
        print("   - Clean up import statements")
        print("   - Add missing | None for default None parameters")
        print("\n🧪 Run './check_types.py' to verify!")

if __name__ == "__main__":
    main()
