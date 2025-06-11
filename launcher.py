#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiofiles",
#     "fastapi",
#     "jinja2",
#     "mcp",
#     "pydantic",
#     "uvicorn[standard]",
#     "psutil",
# ]
# ///
"""
Launcher script for the Knowledge Graph MCP Server

This script handles:
- Port assignment and tracking
- Process management
- Database backup
- Logging configuration
"""

import argparse
import json
import logging
import os
import shutil
import socket
import sys
import time
from pathlib import Path
from typing import Optional

import psutil


def setup_logging(memgraph_dir: Path) -> None:
    """Setup logging to the memgraph directory."""
    log_file = memgraph_dir / "memgraph.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def find_free_port(start_port: int = 8080, max_attempts: int = 100) -> int:
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + max_attempts}")


def is_process_running(pid: int) -> bool:
    """Check if a process is running."""
    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def backup_database(memgraph_dir: Path) -> None:
    """Create a backup of the database if it exists."""
    db_file = Path("knowledge_graph.db")
    backup_dir = memgraph_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    
    if db_file.exists():
        backup_file = backup_dir / f"knowledge_graph_{int(time.time())}.db"
        shutil.copy2(db_file, backup_file)
        logging.info(f"Database backed up to {backup_file}")
        
        # Keep only the 5 most recent backups
        backups = sorted(backup_dir.glob("knowledge_graph_*.db"), 
                        key=lambda x: x.stat().st_mtime, reverse=True)
        for old_backup in backups[5:]:
            old_backup.unlink()
            logging.info(f"Removed old backup {old_backup}")


def save_server_info(memgraph_dir: Path, port: int, pid: int) -> None:
    """Save server information to files."""
    (memgraph_dir / "port").write_text(str(port))
    (memgraph_dir / "pid").write_text(str(pid))
    
    # Also save as JSON for easier parsing
    info = {"port": port, "pid": pid, "timestamp": time.time()}
    (memgraph_dir / "server_info.json").write_text(json.dumps(info, indent=2))


def cleanup_stale_info(memgraph_dir: Path) -> None:
    """Clean up stale server info if process is not running."""
    pid_file = memgraph_dir / "pid"
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            if not is_process_running(old_pid):
                logging.info(f"Cleaning up stale server info for PID {old_pid}")
                pid_file.unlink(missing_ok=True)
                (memgraph_dir / "port").unlink(missing_ok=True)
                (memgraph_dir / "server_info.json").unlink(missing_ok=True)
        except (ValueError, FileNotFoundError):
            pass


def check_server_status(memgraph_dir: Path) -> Optional[dict]:
    """Check if a server is already running."""
    server_info_file = memgraph_dir / "server_info.json"
    if server_info_file.exists():
        try:
            info = json.loads(server_info_file.read_text())
            if is_process_running(info["pid"]):
                return info
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            pass
    return None


def main() -> None:
    """Main launcher function."""
    parser = argparse.ArgumentParser(description="Launch the Knowledge Graph MCP Server")
    parser.add_argument("--port", type=int, help="Specific port to use (default: auto-assign)")
    parser.add_argument("--stdio", action="store_true", help="Use stdio mode instead of HTTP server")
    parser.add_argument("--status", action="store_true", help="Check server status")
    parser.add_argument("--stop", action="store_true", help="Stop running server")
    parser.add_argument("--data-dir", type=Path, help="Data directory (default: ~/.memgraph)")
    
    args = parser.parse_args()
    
    # Setup memgraph directory
    if args.data_dir:
        memgraph_dir = args.data_dir
    else:
        memgraph_dir = Path.home() / ".memgraph"
    
    memgraph_dir.mkdir(exist_ok=True)
    setup_logging(memgraph_dir)
    
    logging.info("Memgraph launcher started")
    
    # Handle status check
    if args.status:
        status = check_server_status(memgraph_dir)
        if status:
            print(f"Server running on port {status['port']} (PID: {status['pid']})")
            sys.exit(0)
        else:
            print("No server running")
            sys.exit(1)
    
    # Handle stop command
    if args.stop:
        status = check_server_status(memgraph_dir)
        if status:
            try:
                psutil.Process(status["pid"]).terminate()
                print(f"Stopped server on port {status['port']} (PID: {status['pid']})")
                # Clean up files after a brief delay
                time.sleep(1)
                cleanup_stale_info(memgraph_dir)
                sys.exit(0)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"Error stopping server: {e}")
                cleanup_stale_info(memgraph_dir)
                sys.exit(1)
        else:
            print("No server running")
            sys.exit(1)
    
    # Clean up any stale info
    cleanup_stale_info(memgraph_dir)
    
    # Check if server is already running
    status = check_server_status(memgraph_dir)
    if status:
        print(f"Server already running on port {status['port']} (PID: {status['pid']})")
        print(f"Use --stop to stop it or --status to check status")
        sys.exit(1)
    
    # Create database backup
    backup_database(memgraph_dir)
    
    if args.stdio:
        # STDIO mode - not recommended for Docker
        logging.warning("Using STDIO mode - not recommended for Docker deployment")
        from memgraph.server import run_stdio_server
        run_stdio_server()
    else:
        # HTTP server mode (recommended)
        port = args.port or find_free_port()
        
        logging.info(f"Starting server on port {port}")
        
        # Save server info before starting (we'll update with actual PID after fork)
        save_server_info(memgraph_dir, port, os.getpid())
        
        # Start the server
        from memgraph.server import run_server
        
        try:
            print(f"Starting Knowledge Graph MCP Server on port {port}")
            print(f"Web interface will be available at http://localhost:{port}")
            print(f"Logs and data stored in: {memgraph_dir}")
            run_server(port=port, host="0.0.0.0")
        except KeyboardInterrupt:
            logging.info("Server stopped by user")
            cleanup_stale_info(memgraph_dir)
        except Exception as e:
            logging.error(f"Server error: {e}")
            cleanup_stale_info(memgraph_dir)
            sys.exit(1)


if __name__ == "__main__":
    main()
