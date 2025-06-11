#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click>=8.1.0",
#     "rich>=13.9.0",
# ]
# ///
"""
Zabob Memgraph Migration Helper

Helps transition from the old Makefile-based structure to the new Click-based CLI structure.
"""

import os
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.command()
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def migrate(dry_run: bool):
    """Migrate from old structure to new zabob-memgraph structure"""

    console.print(Panel(
        "🔄 Zabob Memgraph Migration Helper\n"
        "Transition from Makefile to Click-based CLI",
        title="Migration Tool"
    ))

    project_dir = Path(".")

    # Files that can be removed
    removable_files = [
        "launcher.py.old",
        "install.sh.old",
        "Makefile",  # After confirming dev script works
    ]

    # Files that should be renamed/updated
    updates_needed = [
        ("README.md", "README-old.md", "README-new.md"),
    ]

    console.print("\\n📋 Migration Plan:")

    # Show removable files
    table = Table(title="Files that can be removed")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Reason")

    for file in removable_files:
        file_path = project_dir / file
        if file_path.exists():
            table.add_row(file, "✅ Exists", "Replaced by new CLI structure")
        else:
            table.add_row(file, "❌ Missing", "Already removed")

    console.print(table)

    # Show command mapping
    console.print("\\n🔄 Command Migration Guide:")

    cmd_table = Table(title="Old vs New Commands")
    cmd_table.add_column("Old Command", style="red")
    cmd_table.add_column("New Command", style="green")

    commands = [
        ("make install", "./zabob-memgraph-dev.py install"),
        ("make run", "./zabob-memgraph-dev.py run"),
        ("make run-port PORT=8080", "./zabob-memgraph-dev.py run --port 8080"),
        ("make docker-build", "./zabob-memgraph-dev.py build"),
        ("make docker-run", "./zabob-memgraph-dev.py docker-run"),
        ("make test", "./zabob-memgraph-dev.py test"),
        ("make lint", "./zabob-memgraph-dev.py lint"),
        ("make clean", "./zabob-memgraph-dev.py clean"),
        ("uv run launcher.py", "zabob-memgraph start"),
        ("uv run launcher.py --status", "zabob-memgraph status"),
        ("uv run launcher.py --stop", "zabob-memgraph stop"),
    ]

    for old, new in commands:
        cmd_table.add_row(old, new)

    console.print(cmd_table)

    if not dry_run:
        console.print("\\n⚠️  Use --dry-run first to see what would be changed")
        return

    console.print("\\n✅ Migration plan complete!")
    console.print("\\n📝 Next steps:")
    console.print("1. Test the new commands work correctly")
    console.print("2. Update your workflows to use new commands")
    console.print("3. Remove old files: rm Makefile launcher.py.old install.sh.old")
    console.print("4. Replace README.md with README-new.md")
    console.print("5. Update repository documentation")


@click.command()
def test_new_structure():
    """Test that the new CLI structure works"""
    console.print("🧪 Testing new CLI structure...")

    scripts = [
        ("zabob-memgraph-launcher.py", "zabob-memgraph start --help"),
        ("zabob-memgraph-dev.py", "./zabob-memgraph-dev.py --help"),
        ("zabob-memgraph-install.py", "./zabob-memgraph-install.py --help"),
    ]

    all_good = True

    for script, test_cmd in scripts:
        script_path = Path(script)
        if script_path.exists():
            console.print(f"✅ {script} exists")
            if script_path.stat().st_mode & 0o111:  # Check if executable
                console.print(f"✅ {script} is executable")
            else:
                console.print(f"⚠️  {script} needs execute permission")
                console.print(f"   Run: chmod +x {script}")
                all_good = False
        else:
            console.print(f"❌ {script} missing")
            all_good = False

    if all_good:
        console.print("\\n🎉 New CLI structure looks good!")
    else:
        console.print("\\n❌ Some issues need to be fixed")


@click.group()
def cli():
    """Zabob Memgraph Migration Helper"""
    pass


cli.add_command(migrate)
cli.add_command(test_new_structure)


if __name__ == "__main__":
    cli()
