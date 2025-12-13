#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
#     "rich",
# ]
# ///
"""
Development utility script for testing the memgraph server
"""

import time

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def test_server(base_url="http://localhost:6789"):
    """Test server endpoints and functionality"""

    console.print(Panel(f"Testing Memgraph Server at {base_url}",
                        title="🧪 Server Test"))

    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            console.print("✅ Health check passed")
            console.print(f"   Version: {health_data.get('version', 'unknown')}")
            console.print(f"   Features: {', '.join(health_data.get('features', []))}")
        else:
            console.print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.RequestException as e:
        console.print(f"❌ Could not connect to server: {e}")
        return False

    # Test knowledge graph endpoint
    try:
        response = requests.get(f"{base_url}/api/knowledge-graph",
                                timeout=10)
        if response.status_code == 200:
            graph_data = response.json()
            console.print("✅ Knowledge graph endpoint working")
            console.print(f"   Entities: {len(graph_data.get('nodes', []))}")
            console.print(f"   Relations: {len(graph_data.get('links', []))}")
        else:
            console.print(f"❌ Knowledge graph failed: {response.status_code}")
    except requests.RequestException as e:
        console.print(f"❌ Knowledge graph error: {e}")

    # Test search endpoint
    try:
        response = requests.get(f"{base_url}/api/search?q=test",
                                timeout=5)
        if response.status_code == 200:
            search_results = response.json()
            console.print("✅ Search endpoint working")
            console.print(f"   Results for 'test': {len(search_results)}")
        else:
            console.print(f"❌ Search failed: {response.status_code}")
    except requests.RequestException as e:
        console.print(f"❌ Search error: {e}")

    # Test entity creation
    test_entity = {
        "name": f"Test Entity {int(time.time())}",
        "entityType": "test",
        "observations": ["This is a test observation", "Created by dev script"]
    }

    try:
        response = requests.post(
            f"{base_url}/api/entities",
            json=[test_entity],
            timeout=5
        )
        if response.status_code == 200:
            console.print("✅ Entity creation working")
        else:
            console.print(f"❌ Entity creation failed: {response.status_code}")
    except requests.RequestException as e:
        console.print(f"❌ Entity creation error: {e}")

    console.print("\n🎉 Server test complete!")
    return True


def show_server_stats(base_url="http://localhost:6789"):
    """Display server statistics"""

    try:
        # Get database stats
        response = requests.get(f"{base_url}/api/database-stats",
                                timeout=5)
        if response.status_code == 200:
            stats = response.json()

            table = Table(title="📊 Database Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Entities",
                          str(stats.get("total_entities", "N/A")))
            table.add_row("Total Relations",
                          str(stats.get("total_relations", "N/A")))
            table.add_row("Database Size",
                          f"{stats.get('database_size_mb', 0):.2f} MB")
            table.add_row("Backend Type",
                          stats.get("backend_type", "Unknown"))

            console.print(table)
        else:
            console.print(f"❌ Could not get stats: {response.status_code}")

    except requests.RequestException as e:
        console.print(f"❌ Stats error: {e}")


def monitor_server(base_url="http://localhost:6789", interval=5):
    """Monitor server health continuously"""

    console.print(Panel(f"Monitoring server at {base_url} "
                        "(Ctrl+C to stop)", title="📡 Server Monitor"))

    try:
        while True:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Checking server...", total=None)

                try:
                    response = requests.get(f"{base_url}/health", timeout=3)
                    if response.status_code == 200:
                        timestamp = time.strftime("%H:%M:%S")
                        console.print(f"[green]{timestamp}[/green] ✅ Server healthy "
                                      "- {health.get('status', 'unknown')}")
                    else:
                        timestamp = time.strftime("%H:%M:%S")
                        console.print(f"[red]{timestamp}[/red] ❌ Server unhealthy "
                                      "- HTTP {response.status_code}")

                except requests.RequestException:
                    timestamp = time.strftime("%H:%M:%S")
                    console.print(f"[red]{timestamp}[/red] ❌ Server unreachable")

                progress.remove_task(task)

            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n👋 Monitoring stopped")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Memgraph development utilities")
    parser.add_argument("--url", default="http://localhost:6789", help="Server URL")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test server endpoints")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show server statistics")

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor server health")
    monitor_parser.add_argument("--interval", type=int, default=5, help="Check interval in seconds")

    args = parser.parse_args()

    if args.command == "test":
        test_server(args.url)
    elif args.command == "stats":
        show_server_stats(args.url)
    elif args.command == "monitor":
        monitor_server(args.url, args.interval)
    else:
        console.print("Available commands: test, stats, monitor")
        console.print("Example: uv run dev_utils.py test")
