"""Helpers for application-owned temporary files."""

import shutil
from pathlib import Path

from src.utils.logging import logger
from src.utils.paths import get_tmp_dir_path

# --------------------------------------------------------------------------------------------------
# Temporary files
# --------------------------------------------------------------------------------------------------
def get_tmp_file_path(relative_path: str) -> Path:
    """Create parent directories under tmp and return the resolved file path."""
    full_path = get_tmp_dir_path() / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    return full_path
# --------------------------------------------------------------------------------------------------
def create_file(relative_path: str, content: bytes | str, permissions: int | None = None) -> Path:
    """Write content under tmp and return the resulting file path."""
    full_path = get_tmp_file_path(relative_path)
    if isinstance(content, str):
        full_path.write_text(content, encoding="utf-8", newline="\n")
    else:
        full_path.write_bytes(content)
    if permissions is not None:
        full_path.chmod(permissions)
    logger.debug(f"Wrote temporary file: {full_path}")
    return full_path
# --------------------------------------------------------------------------------------------------
def clean_tmp_dir() -> bool:
    """Remove the application temporary directory and its contents."""
    tmp_dir_path = get_tmp_dir_path()
    if not tmp_dir_path.exists():
        return False
    shutil.rmtree(tmp_dir_path)
    logger.info(f"Cleaned temporary directory: {tmp_dir_path}")
    return True
