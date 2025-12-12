#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click>=8.3.1",
#     "requests>=2.32.5",
#     "rich>=14.2.0",
# ]
# ///
"""
Zabob Memgraph Installation Script

A self-contained Python script that installs Zabob Memgraph and its dependencies.
Uses PEP-723 for dependency management with uv.
"""

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    print("❌ Required dependencies not available.")
    print("This script requires uv to run. Please install uv first:")
    print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
    sys.exit(1)

console = Console()

GITHUB_REPO = "BobKerns/zabob-memgraph"  # Update this
LAUNCHER_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/zabob-memgraph-launcher.py"


@click.command()
@click.option("--install-dir", type=click.Path(path_type=Path),
              default=Path.home() / ".local" / "bin",
              help="Directory to install launcher script")
@click.option("--config-dir", type=click.Path(path_type=Path),
              default=Path.home() / ".zabob-memgraph",
              help="Configuration directory")
@click.option("--check-deps", is_flag=True,
              help="Only check dependencies, don't install")
@click.option("--skip-docker", is_flag=True,
              help="Skip Docker installation check")
def install(install_dir: Path, config_dir: Path, check_deps: bool, skip_docker: bool):
    """Install Zabob Memgraph Knowledge Graph Server"""

    console.print(Panel(
        "🧠 Zabob Memgraph Installation\\n"
        "Knowledge Graph Server for MCP",
        title="Welcome"
    ))

    if check_deps:
        check_dependencies(skip_docker)
        return

    # Create directories
    install_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"📁 Install directory: {install_dir}")
    console.print(f"⚙️  Config directory: {config_dir}")

    # Check dependencies
    deps_ok = check_dependencies(skip_docker)
    if not deps_ok:
        console.print("❌ Please install missing dependencies first")
        sys.exit(1)

    # Download launcher script
    console.print("📥 Downloading launcher script...")
    launcher_path = install_dir / "zabob-memgraph"

    try:
        download_launcher(launcher_path)
        console.print(f"✅ Launcher installed: {launcher_path}")
    except Exception as e:
        console.print(f"❌ Failed to download launcher: {e}")
        console.print("You can manually download from:")
        console.print(f"   {LAUNCHER_URL}")
        sys.exit(1)

    # Make executable
    try:
        launcher_path.chmod(0o755)
    except Exception as e:
        console.print(f"⚠️  Could not make launcher executable: {e}")
        console.print(f"Run: chmod +x {launcher_path}")

    # Add to PATH if needed
    check_path(install_dir)

    # Create initial config
    create_initial_config(config_dir)

    console.print(Panel(
        f"""
✅ Installation complete!

🚀 To get started:
   zabob-memgraph start

📊 Check status:
   zabob-memgraph status

🐳 Use Docker:
   zabob-memgraph start --docker

📚 Get help:
   zabob-memgraph --help

Config directory: {config_dir}
""",
        title="🎉 Success!"
    ))


def check_dependencies(skip_docker: bool = False) -> bool:
    """Check if required dependencies are installed"""
    console.print("🔍 Checking dependencies...")

    all_good = True

    # Check Python version
    if sys.version_info < (3, 12):
        console.print("❌ Python 3.12+ required")
        all_good = False
    else:
        console.print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")

    # Check uv
    if shutil.which("uv"):
        try:
            result = subprocess.run(["uv", "--version"],
                                    capture_output=True, text=True, check=True)
            version = result.stdout.strip()
            console.print(f"✅ uv {version}")
        except subprocess.CalledProcessError:
            console.print("❌ uv found but not working properly")
            all_good = False
    else:
        console.print("❌ uv not found")
        console.print("   Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        all_good = False

    # Check Docker (optional)
    if not skip_docker:
        if shutil.which("docker"):
            try:
                result = subprocess.run(["docker", "--version"],
                                        capture_output=True, text=True, check=True)
                version = result.stdout.strip()
                console.print(f"✅ Docker available: {version}")
            except subprocess.CalledProcessError:
                console.print("⚠️  Docker found but not working")
        else:
            console.print("⚠️  Docker not found (optional)")
            console.print("   Install from: https://docs.docker.com/get-docker/")

    # Check curl or wget
    if shutil.which("curl"):
        console.print("✅ curl available")
    elif shutil.which("wget"):
        console.print("✅ wget available")
    else:
        console.print("❌ Neither curl nor wget found")
        console.print("   Install curl or wget for downloading")
        all_good = False

    return all_good


def download_launcher(target_path: Path) -> None:
    """Download the launcher script"""

    # Try different download methods
    if shutil.which("curl"):
        cmd = ["curl", "-L", "-o", str(target_path), LAUNCHER_URL]
        subprocess.run(cmd, check=True)
    elif shutil.which("wget"):
        cmd = ["wget", "-O", str(target_path), LAUNCHER_URL]
        subprocess.run(cmd, check=True)
    else:
        # Fallback to urllib (though this might not work for all URLs)
        with urllib.request.urlopen(LAUNCHER_URL) as response:
            target_path.write_bytes(response.read())


def check_path(install_dir: Path) -> None:
    """Check if install directory is in PATH"""
    path_env = os.environ.get("PATH", "")
    path_dirs = path_env.split(os.pathsep)

    if str(install_dir) in path_dirs:
        console.print(f"✅ {install_dir} is in PATH")
    else:
        console.print(f"⚠️  {install_dir} is not in PATH")

        # Detect shell and suggest addition
        shell = os.environ.get("SHELL", "/bin/bash")
        shell_name = Path(shell).name

        if shell_name in ["bash", "sh"]:
            rc_file = Path.home() / ".bashrc"
        elif shell_name == "zsh":
            rc_file = Path.home() / ".zshrc"
        elif shell_name == "fish":
            rc_file = Path.home() / ".config" / "fish" / "config.fish"
        else:
            rc_file = None

        console.print("Add to your shell configuration:")
        if shell_name == "fish":
            console.print(f"   echo 'set -gx PATH {install_dir} $PATH' >> {rc_file}")
        else:
            console.print(f"   echo 'export PATH={install_dir}:$PATH' >> {rc_file}")
        console.print("   source ~/.bashrc  # or restart your terminal")


def create_initial_config(config_dir: Path) -> None:
    """Create initial configuration files"""
    config_file = config_dir / "config.json"

    if config_file.exists():
        console.print("⚙️  Configuration already exists")
        return

    initial_config = {
        "version": "1.0",
        "default_port": 6789,
        "default_host": "localhost",
        "mode": "auto",  # auto, stdio, server
        "docker_image": "zabob-memgraph:latest",
        "data_dir": str(config_dir / "data"),
        "log_level": "INFO"
    }

    import json
    config_file.write_text(json.dumps(initial_config, indent=2))

    # Create data directory
    (config_dir / "data").mkdir(exist_ok=True)

    console.print(f"⚙️  Created initial configuration: {config_file}")


@click.command()
@click.option("--config-dir", type=click.Path(path_type=Path),
              default=Path.home() / ".zabob-memgraph",
              help="Configuration directory")
def uninstall(config_dir: Path):
    """Uninstall Zabob Memgraph"""
    console.print("🗑️  Uninstalling Zabob Memgraph...")

    # Find and remove launcher
    install_dirs = [
        Path.home() / ".local" / "bin",
        Path("/usr/local/bin"),
        Path("/opt/homebrew/bin")
    ]

    removed_launcher = False
    for install_dir in install_dirs:
        launcher_path = install_dir / "zabob-memgraph"
        if launcher_path.exists():
            try:
                launcher_path.unlink()
                console.print(f"✅ Removed launcher: {launcher_path}")
                removed_launcher = True
            except Exception as e:
                console.print(f"❌ Could not remove {launcher_path}: {e}")

    if not removed_launcher:
        console.print("⚠️  No launcher found in common locations")

    # Ask about config directory
    if config_dir.exists():
        if click.confirm(f"Remove configuration directory {config_dir}?"):
            try:
                shutil.rmtree(config_dir)
                console.print(f"✅ Removed config directory: {config_dir}")
            except Exception as e:
                console.print(f"❌ Could not remove config directory: {e}")

    console.print("✅ Uninstall complete")


@click.group()
def cli():
    """Zabob Memgraph Installation Manager"""
    pass


cli.add_command(install)
cli.add_command(uninstall)


if __name__ == "__main__":
    cli()
