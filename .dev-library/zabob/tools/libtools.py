#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.3.1",
#     "gitpython>=3.1.46",
#     "rich>=14.3.2",
# ]
# ///
"""
Dev Library Tools - Manage Zabob development library integration.

This module provides CLI commands for managing the .dev-library git subtree
in Zabob projects. Can be run standalone or imported into project-specific
dev tools.

Usage:
    # Standalone
    uv run .dev-library/zabob/tools/libtools.py pull

    # Imported (requires editable dev dependency in pyproject.toml):
    # [tool.uv]
    # dev-dependencies = [
    #     "zabob-dev-library = { path = ".dev-library", editable = true }",
    # ]
    from zabob.tools.libtools import cli as devlib_cli
    from zabob.tools.libtools import DevLibraryManager
"""

from collections.abc import Sequence
from pathlib import Path
from typing import NotRequired, TypedDict
import subprocess
import shutil
import sys

import click
from git import GitCommandError, Repo

from rich.console import Console
from rich.panel import Panel

console = Console()
# Types
class DevLibraryStatus(TypedDict):
    """Status information for dev-library integration."""
    exists: bool
    prefix: str
    remote_url: str
    branch: str
    repo_root: str
    uncommitted_changes: NotRequired[int]  # Only present if exists=True
    changed_files: NotRequired[list[str]]  # Only present if exists=True
    untracked_files: NotRequired[list[str]]  # Only present if exists=True


class Config(TypedDict):
    """Global configuration for check commands."""
    paths: list[Path]
    checks: list[click.Command]
    config: Path | None  # Path to config file (optional)


# Constants
DEV_LIBRARY = Path(__file__).parent.parent.parent.resolve()
DEFAULT_REMOTE = "git@github.com:BobKerns/zabob-dev-library.git"
DEFAULT_PREFIX = ".dev-library"
DEFAULT_BRANCH = "main"

# Global configuration for check commands
# Projects can override these before using the CLI
CONFIG: Config = {
    "paths": [
        DEV_LIBRARY / 'zabob'
    ],
    "checks": [],
    "config": None,  # Path to config file (optional)
}


class DevLibraryManager:
    """Manage git subtree operations for .dev-library."""

    def __init__(
        self,
        repo_path: Path | None = None,
        prefix: str = DEFAULT_PREFIX,
        remote_url: str = DEFAULT_REMOTE,
        branch: str = DEFAULT_BRANCH,
    ):
        """Initialize manager with repository context."""
        initial_path = repo_path or Path.cwd()
        self.prefix = prefix
        self.remote_url = remote_url
        self.branch = branch

        try:
            self.repo = Repo(initial_path, search_parent_directories=True)
            # Use the actual repo root, not the initial path
            self.repo_path = Path(self.repo.working_dir)
        except Exception as e:
            raise click.ClickException(f"Not a git repository: {e}") from e

    def _run_subtree_cmd(self, operation: str, squash: bool = False) -> str:
        """Run git subtree command and return output."""
        try:
            match operation:
                case "add" | "pull" | "push":
                    result: str = self.repo.git.subtree(
                        operation,
                        f"--prefix={self.prefix}",
                        self.remote_url,
                        self.branch,
                        *(("--squash",) if squash else ()),
                    )
                case _:
                    raise click.ClickException(
                        f"Unsupported git subtree operation: {operation}"
                    )
            return result
        except GitCommandError as e:
            msg = f"Git subtree {operation} failed: {e}"
            raise click.ClickException(msg) from e

    def add(self, squash: bool = True) -> str:
        """Add dev-library as subtree (one-time setup)."""
        click.echo(f"Adding {self.prefix} from {self.remote_url}...")
        result = self._run_subtree_cmd("add", squash=squash)
        click.secho(f"✓ Dev library added to {self.prefix}", fg="green")
        return result

    def pull(self, squash: bool = True) -> str:
        """Pull updates from dev-library."""
        click.echo(f"Pulling updates to {self.prefix}...")
        result = self._run_subtree_cmd("pull", squash=squash)
        click.secho(f"✓ Dev library updated", fg="green")
        return result

    def push(self) -> str:
        """Push improvements back to dev-library."""
        click.echo(f"Pushing changes from {self.prefix}...")
        result = self._run_subtree_cmd("push")
        click.secho(f"✓ Changes pushed to dev library", fg="green")
        return result

    def status(self) -> DevLibraryStatus:
        """Get status of dev-library integration."""
        lib_path = self.repo_path / self.prefix

        status: DevLibraryStatus = {
            "exists": lib_path.exists(),
            "prefix": self.prefix,
            "remote_url": self.remote_url,
            "branch": self.branch,
            "repo_root": str(self.repo.working_dir),
        }

        if status["exists"]:
            # Check for modified tracked files in .dev-library
            changed_files = [
                item.a_path for item in self.repo.index.diff(None)
                if item.a_path and item.a_path.startswith(self.prefix)
            ]
            # Check for untracked files in .dev-library
            untracked_files = [
                path for path in self.repo.untracked_files
                if path.startswith(self.prefix)
            ]

            total_changes = len(changed_files) + len(untracked_files)
            status["uncommitted_changes"] = total_changes
            status["changed_files"] = changed_files
            status["untracked_files"] = untracked_files

        return status


# Root CLI group
@click.group()
def cli():
    """Zabob development tools."""
    pass


# Library management commands group
@cli.group(name="tools")
@click.option(
    "--prefix",
    default=DEFAULT_PREFIX,
    help="Subtree prefix path",
    show_default=True,
)
@click.option(
    "--remote",
    default=DEFAULT_REMOTE,
    help="Remote repository URL",
    show_default=True,
)
@click.option(
    "--branch",
    default=DEFAULT_BRANCH,
    help="Remote branch name",
    show_default=True,
)
@click.pass_context
def tools(ctx, prefix: str, remote: str, branch: str):
    """Manage dev-library subtree integration."""
    ctx.ensure_object(dict)
    ctx.obj["manager"] = DevLibraryManager(
        prefix=prefix,
        remote_url=remote,
        branch=branch,
    )


@tools.command()
@click.option("--no-squash", is_flag=True, help="Don't squash commits")
@click.pass_context
def add(ctx, no_squash: bool):
    """Add dev-library as subtree (one-time setup)."""
    manager: DevLibraryManager = ctx.obj["manager"]
    manager.add(squash=not no_squash)


@tools.command()
@click.option("--no-squash", is_flag=True, help="Don't squash commits")
@click.pass_context
def pull(ctx, no_squash: bool):
    """Pull updates from dev-library."""
    manager: DevLibraryManager = ctx.obj["manager"]
    manager.pull(squash=not no_squash)


@tools.command()
@click.pass_context
def push(ctx):
    """Push improvements back to dev-library."""
    manager: DevLibraryManager = ctx.obj["manager"]
    manager.push()


@tools.command()
@click.pass_context
def status(ctx):
    """Show dev-library integration status."""
    manager: DevLibraryManager = ctx.obj["manager"]
    info = manager.status()

    click.echo(f"\n📚 Dev Library Status")
    click.echo(f"{'─' * 50}")
    click.echo(f"Repository:   {info['repo_root']}")
    click.echo(f"Prefix:       {info['prefix']}")
    click.echo(f"Remote:       {info['remote_url']}")
    click.echo(f"Branch:       {info['branch']}")
    click.echo(f"Exists:       {'✓' if info['exists'] else '✗'}")

    if info["exists"]:
        changes = info.get("uncommitted_changes", 0)
        if changes > 0:
            click.secho(f"\n⚠ Uncommitted changes: {changes} file(s)", fg="yellow")

            # Show modified files
            changed = info.get("changed_files", [])
            if changed:
                click.echo(f"\n  Modified:")
                for file in changed[:5]:
                    click.echo(f"    • {file}")
                if len(changed) > 5:
                    click.echo(f"    ... and {len(changed) - 5} more")

            # Show untracked files
            untracked = info.get("untracked_files", [])
            if untracked:
                click.echo(f"\n  Untracked:")
                for file in untracked[:5]:
                    click.echo(f"    • {file}")
                if len(untracked) > 5:
                    click.echo(f"    ... and {len(untracked) - 5} more")
        else:
            click.secho(f"\n✓ No uncommitted changes", fg="green")

    click.echo()


# Check commands group (separate from library management)
@cli.group()
def code():
    """Run code quality and maintenance checks."""
    pass


@code.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output")
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.option("--fix", is_flag=True, help="Automatically fix issues where possible")
def ruff(paths: Sequence[str | Path], verbose: bool, config: Path | None, fix: bool):
    """Run ruff linter on specified paths."""
    import subprocess

    # Use global config if no paths provided
    if not paths:
        paths = CONFIG["paths"] or []
        if not config:
            config = CONFIG.get("config")

    if not paths:
        click.secho("✗ No paths specified and no global config set", fg="red")
        raise SystemExit(1)

    console.print(Panel("Linting with ruff"))
    cmd = ["uv", "run", "--active", "ruff", "check",
           * (["--fix"] if fix else []),
           * (["--config", config] if config else []),
           * (("--verbose",) if verbose else ()),
           * (str(p) for p in paths)
           ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        click.secho("✓ No issues found", fg="green")
    else:
        click.secho(f"✗ Issues found (exit code {result.returncode})", fg="yellow")

    raise SystemExit(result.returncode)


@code.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output")
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
def mypy(paths: Sequence[str | Path], verbose: bool, config: Path | None):
    """Run mypy type checker on specified paths."""
    import subprocess

    # Use global config if no paths provided
    if not paths:
        paths = CONFIG["paths"]
        if not config:
            config = CONFIG.get("config")

    if not paths:
        click.secho("✗ No paths specified and no global config set", fg="red")
        raise SystemExit(1)

    console.print(Panel("Type Checking with mypy"))

    cmd = ["uv", "run", "--active", "mypy",
           * (["--config-file", config] if config else []),
           * (("--verbose",) if verbose else ()),
           * (str(p) for p in paths)
           ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        console.print("✓ No type errors", style="green")
    else:
        console.print(f"✗ Type errors found (exit code {result.returncode})", style="yellow")

    raise SystemExit(result.returncode)


@click.command(name="format")
def format_code() -> None:
    """Format code with ruff"""
    project_root = Path(__file__).parent.parent
    console.print("✨ Formatting code with ruff...")

    result = subprocess.run(["uv", "run", "ruff", "format", "."], cwd=project_root, check=False)

    if result.returncode == 0:
        console.print("✅ Code formatted successfully!")
    else:
        console.print("❌ Formatting failed")
        sys.exit(1)


@click.command()
def clean() -> None:
    """Clean build artifacts and cache"""
    project_root = Path(__file__).parent.parent
    console.print("🧹 Cleaning build artifacts...")

    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.egg-info",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    ]

    count = 0
    for pattern in patterns:
        for path in project_root.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            count += 1

    console.print(f"✅ Cleaned {count} items")


CONFIG["checks"].extend([ruff, mypy])


@code.command("all")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Show detailed output")
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.option("--fix", is_flag=True, help="Automatically fix issues where possible")
@click.pass_context
def all_checks(ctx: click.Context,
               paths: Sequence[str | Path]=(),
               verbose: bool = False, config: str | None = None,
               fix: bool = False):
    """Run all checks (ruff + mypy) on specified paths."""
    exitcode: str | int = 0
    for check in CONFIG["checks"]:
        try:
            ctx.invoke(
                check,
                config=config,
                **(dict(fix=fix) if check == ruff else {}),
            )
        except SystemExit as e:
            if e.code is not None and e.code != 0:
                exitcode = e.code

    raise SystemExit(exitcode)


if __name__ == "__main__":
    cli()
