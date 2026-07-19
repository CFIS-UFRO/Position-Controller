"""Console and rotating-file logging configuration."""

import logging
import re
import sys
import traceback
from collections.abc import Sequence
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import TextIO

from colorlog import ColoredFormatter

from src.utils.paths import get_log_file_path

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------
ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x1b]*(?:\x1b\\|\x07))"
)
LOG_SEPARATOR = "=" * 80

# --------------------------------------------------------------------------------------------------
# Formatters and handlers
# --------------------------------------------------------------------------------------------------
class StripAnsiFormatter(logging.Formatter):
    """Format a record after removing ANSI escape sequences."""

    def format(self, record: logging.LogRecord) -> str:
        return ANSI_ESCAPE_RE.sub("", super().format(record))
# --------------------------------------------------------------------------------------------------
class StreamToLogger:
    """Redirect a text stream to the configured logger."""

    def __init__(self, target_logger: logging.Logger, level: int, original_stream: TextIO | None) -> None:
        self._logger = target_logger
        self._level = level
        self._original_stream = original_stream

    def write(self, message: str) -> None:
        if message.strip():
            self._logger.log(self._level, message.rstrip())

    def flush(self) -> None:
        if self._original_stream is not None:
            self._original_stream.flush()

    def isatty(self) -> bool:
        return self._original_stream.isatty() if self._original_stream is not None else False
# --------------------------------------------------------------------------------------------------
class ExceptionHandler:
    """Log uncaught exceptions with their complete traceback."""

    def __init__(self, target_logger: logging.Logger) -> None:
        self._logger = target_logger

    def __call__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        full_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self._logger.critical("Uncaught exception:\n%s", full_traceback)

# --------------------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------------------
def init_logging() -> Path:
    """Configure console, rotating-file, stream, warning, and exception logging."""
    log_file_path = get_log_file_path()
    if getattr(logger, "_position_controller_initialized", False):
        return log_file_path
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s] %(message)s%(reset)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.__stdout__)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    file_formatter = StripAnsiFormatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_file_path,
        mode="a",
        maxBytes=10 * 1024 * 1024,
        backupCount=4,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    sys.stdout = StreamToLogger(logger, logging.INFO, sys.__stdout__)
    sys.stderr = StreamToLogger(logger, logging.ERROR, sys.__stderr__)
    sys.excepthook = ExceptionHandler(logger)
    logging.captureWarnings(True)
    setattr(logger, "_position_controller_initialized", True)
    return log_file_path
# --------------------------------------------------------------------------------------------------
def log_tree(items: Sequence[str], header: str | None = None, level: int = logging.INFO) -> None:
    """Log a sequence of items using compact tree branches."""
    if header is not None:
        logger.log(level, header)
    last_index = len(items) - 1
    for index, item in enumerate(items):
        branch = "└──" if index == last_index else "├──"
        logger.log(level, f"{branch} {item}")

# --------------------------------------------------------------------------------------------------
# Shared logger
# --------------------------------------------------------------------------------------------------
logger = logging.getLogger()
