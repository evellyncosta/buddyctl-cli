"""Logging configuration for buddyctl."""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(debug: bool = False) -> Path:
    """Setup logging configuration.

    Args:
        debug: Enable debug mode with detailed logging

    Returns:
        Path to the log file
    """
    # Create logs directory
    log_dir = Path.home() / ".buddyctl" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"buddyctl-{timestamp}.log"

    # Configure logging level
    level = logging.DEBUG if debug else logging.INFO

    # File handler - always DEBUG level for detailed logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler - only WARNING and above (errors visible to user)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info(f"BuddyCtl started - Debug mode: {'enabled' if debug else 'disabled'}")
    logger.info(f"Log file: {log_file}")
    logger.info("="*60)

    # Cleanup old logs
    cleanup_old_logs()

    return log_file


def cleanup_old_logs(max_logs: int = 10):
    """Keep only the N most recent log files.

    Args:
        max_logs: Maximum number of log files to keep
    """
    log_dir = Path.home() / ".buddyctl" / "logs"

    if not log_dir.exists():
        return

    # Get all log files sorted by modification time (newest first)
    log_files = sorted(
        log_dir.glob("buddyctl-*.log"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    # Remove old logs
    for old_log in log_files[max_logs:]:
        try:
            old_log.unlink()
            logging.debug(f"Deleted old log file: {old_log}")
        except Exception as e:
            logging.warning(f"Failed to delete old log {old_log}: {e}")


def log_agent_response(logger: logging.Logger, agent_name: str, response: str, level: int = logging.INFO):
    """Log agent response with distinctive visual markers.

    Args:
        logger: Logger instance to use
        agent_name: Name of the agent (e.g., "Main Agent", "Judge Agent", "ReAct Agent")
        response: The response text from the agent
        level: Logging level (default: INFO)
    """
    marker = "=" * 80
    header = f"{'#' * 10} {agent_name.upper()} RESPONSE {'#' * 10}"
    footer = "#" * 80

    logger.log(level, "")
    logger.log(level, marker)
    logger.log(level, header)
    logger.log(level, marker)
    logger.log(level, response)
    logger.log(level, footer)
    logger.log(level, "")


def log_agent_request(logger: logging.Logger, agent_name: str, request: str, level: int = logging.DEBUG):
    """Log agent request with distinctive visual markers.

    Args:
        logger: Logger instance to use
        agent_name: Name of the agent (e.g., "Main Agent", "Judge Agent", "ReAct Agent")
        request: The request text to the agent
        level: Logging level (default: DEBUG)
    """
    marker = "=" * 80
    header = f"{'*' * 10} {agent_name.upper()} REQUEST {'*' * 10}"
    footer = "*" * 80

    logger.log(level, "")
    logger.log(level, marker)
    logger.log(level, header)
    logger.log(level, marker)
    logger.log(level, request)
    logger.log(level, footer)
    logger.log(level, "")
