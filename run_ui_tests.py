#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.3.1",
#     "requests>=2.32.5",
#     "rich>=14.2.0",
# ]
# ///
"""
UI Testing Script for Zabob Memgraph

This script manages the server lifecycle and runs Playwright UI tests.
It ensures the server is running before tests and cleans up afterward.
"""

import subprocess
import sys
import time

import click
import requests
from rich.console import Console

console = Console()


def is_server_running(port: int = 8080) -> bool:
    """Check if the server is running and responsive"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def wait_for_server(port: int = 8080, timeout: int = 30) -> bool:
    """Wait for server to become ready"""
    console.print(f"⏳ Waiting for server on port {port}...")
    start = time.time()

    while time.time() - start < timeout:
        if is_server_running(port):
            console.print("✅ Server is ready")
            return True
        time.sleep(1)

    console.print("❌ Server did not start in time")
    return False


@click.command()
@click.option("--headless/--headed", default=True, help="Run browser in headless mode")
@click.option("--port", default=8080, help="Server port")
@click.option("--keep-server", is_flag=True, help="Don't stop server after tests")
@click.option("-k", "--keyword", help="Run tests matching keyword")
@click.option("-v", "--verbose", is_flag=True, help="Verbose test output")
@click.option("--install", is_flag=True, help="Install Playwright browsers first")
def main(headless: bool, port: int, keep_server: bool, keyword: str | None, verbose: bool, install: bool):
    """Run UI tests with Playwright"""

    if install:
        console.print("📦 Installing Playwright browsers...")
        import shutil
        uv_path = shutil.which("uv") or "uv"
        result = subprocess.run(
            [uv_path, "run", "playwright", "install", "chromium"],
            capture_output=False
        )
        if result.returncode != 0:
            console.print("❌ Failed to install Playwright browsers")
            sys.exit(1)
        console.print("✅ Playwright browsers installed")
        return

    # Check if server is already running
    server_was_running = is_server_running(port)
    server_process = None

    if not server_was_running:
        console.print("🚀 Starting server...")
        try:
            server_process = subprocess.Popen(
                ["./zabob-memgraph-launcher.py", "start"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

            if not wait_for_server(port, timeout=30):
                console.print("❌ Server failed to start")
                if server_process:
                    server_process.terminate()
                sys.exit(1)

        except Exception as e:
            console.print(f"❌ Failed to start server: {e}")
            sys.exit(1)
    else:
        console.print(f"✅ Server already running on port {port}")

    # Build pytest command
    import shutil
    uv_path = shutil.which("uv") or "uv"
    pytest_args = [uv_path, "run", "pytest", "tests/test_ui_playwright.py"]

    if verbose:
        pytest_args.append("-v")

    if keyword:
        pytest_args.extend(["-k", keyword])

    # Set environment variables for headless mode
    env = {}
    if not headless:
        env["PLAYWRIGHT_HEADLESS"] = "false"

    # Run tests
    console.print("🧪 Running UI tests...")
    try:
        result = subprocess.run(
            pytest_args,
            env=env,
            capture_output=False
        )
        test_exit_code = result.returncode
    except KeyboardInterrupt:
        console.print("\n⚠️  Tests interrupted")
        test_exit_code = 130
    except Exception as e:
        console.print(f"❌ Failed to run tests: {e}")
        test_exit_code = 1

    # Clean up server if we started it
    if not server_was_running and not keep_server:
        console.print("🛑 Stopping server...")
        try:
            subprocess.run(
                ["./zabob-memgraph-launcher.py", "stop"],
                capture_output=True,
                timeout=10
            )
            console.print("✅ Server stopped")
        except Exception as e:
            console.print(f"⚠️  Failed to stop server: {e}")

    # Exit with test result code
    if test_exit_code == 0:
        console.print("✅ All tests passed!")
    else:
        console.print(f"❌ Tests failed with exit code {test_exit_code}")

    sys.exit(test_exit_code)


if __name__ == "__main__":
    main()
