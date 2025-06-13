#!/usr/bin/env python3
"""
Service logging utilities for consistent startup and shutdown logging.

Provides context wrappers for synchronous setup and async service phases.
"""

import logging
import sys
import os
from contextlib import contextmanager, asynccontextmanager
from typing import Dict, Any, Optional
import signal
import atexit


class ServiceLogger:
    """Centralized service logging with startup/shutdown tracking."""
    
    def __init__(self, service_name: str, log_file: Optional[str] = None):
        self.service_name = service_name
        self.log_file = log_file
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging with consistent format."""
        if self.log_file:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                filename=self.log_file,
                filemode='a'  # Append to existing log
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                stream=sys.stderr
            )
        
        return logging.getLogger(self.service_name)
    
    def log_startup_args(self, args: Dict[str, Any]) -> None:
        """Log service startup with command-line arguments."""
        self.logger.info(f"=== {self.service_name} Starting ===")
        self.logger.info(f"Command line arguments: {args}")
        self.logger.info(f"Process ID: {os.getpid()}")
        self.logger.info(f"Working directory: {os.getcwd()}")
        
        if self.log_file:
            self.logger.info(f"Logging to file: {self.log_file}")
        else:
            self.logger.info("Logging to stderr")
    
    def log_shutdown(self, reason: str = "normal") -> None:
        """Log service shutdown."""
        self.logger.info(f"=== {self.service_name} Shutdown ({reason}) ===")


@contextmanager
def service_setup_context(service_name: str, args: Dict[str, Any], log_file: Optional[str] = None):
    """
    Context manager for synchronous service setup phase.
    
    Logs startup arguments and handles setup errors.
    """
    service_logger = ServiceLogger(service_name, log_file)
    
    try:
        service_logger.log_startup_args(args)
        service_logger.logger.info("Beginning synchronous setup phase")
        yield service_logger
        service_logger.logger.info("Synchronous setup phase completed successfully")
        
    except Exception as e:
        service_logger.logger.error(f"Setup phase failed: {e}", exc_info=True)
        service_logger.log_shutdown("setup_error")
        raise


@asynccontextmanager
async def service_async_context(service_logger: ServiceLogger):
    """
    Context manager for async service phase (FastAPI lifespan).
    
    Logs service start/stop and handles graceful shutdown.
    """
    def signal_handler(signum, frame):
        service_logger.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        service_logger.log_shutdown("signal")
    
    def exit_handler():
        service_logger.log_shutdown("exit")
    
    try:
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        atexit.register(exit_handler)
        
        service_logger.logger.info("Service startup complete - entering async phase")
        yield
        
    except Exception as e:
        service_logger.logger.error(f"Async phase error: {e}", exc_info=True)
        service_logger.log_shutdown("async_error")
        raise
    finally:
        service_logger.logger.info("Async phase cleanup complete")


def log_app_creation(service_logger: ServiceLogger, app_type: str, config: Dict[str, Any]) -> None:
    """Log FastAPI application creation."""
    service_logger.logger.info(f"Creating {app_type} application")
    service_logger.logger.info(f"Application configuration: {config}")


def log_route_mounting(service_logger: ServiceLogger, route: str, target: str) -> None:
    """Log route mounting for visibility."""
    service_logger.logger.info(f"Mounted route {route} -> {target}")


def log_server_start(service_logger: ServiceLogger, host: str, port: int) -> None:
    """Log server start details."""
    service_logger.logger.info(f"Starting server on {host}:{port}")
    service_logger.logger.info(f"Server URL: http://{host}:{port}")
