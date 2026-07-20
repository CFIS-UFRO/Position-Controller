"""Centralized filesystem paths used by the application."""

from pathlib import Path

from src.config import APP_SLUG

# --------------------------------------------------------------------------------------------------
# Directories
# --------------------------------------------------------------------------------------------------
APP_DIR: Path = Path(__file__).resolve().parents[2]
PROJECT_DIR: Path = APP_DIR.parent
SRC_DIR: Path = APP_DIR / "src"
ASSETS_DIR: Path = SRC_DIR / "assets"
HELP_DIR: Path = ASSETS_DIR / "help"
LOGS_DIR: Path = APP_DIR / "logs"
USER_DATA_DIR: Path = APP_DIR / "usr"
FAKE_SERIAL_PORTS_DIR: Path = USER_DATA_DIR / "fake_serial_ports"
TMP_DIR: Path = APP_DIR / "tmp"

# --------------------------------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------------------------------
PYPROJECT_FILE_PATH: Path = APP_DIR / "pyproject.toml"
UV_LOCK_FILE_PATH: Path = APP_DIR / "uv.lock"
RELEASES_FILE_PATH: Path = APP_DIR / "releases.json"
LOG_FILE_PATH: Path = LOGS_DIR / f"{APP_SLUG}.log"
ICON_FILE_PATH: Path = ASSETS_DIR / "icon.png"
HELP_INDEX_FILE_PATH: Path = HELP_DIR / "index.json"

# --------------------------------------------------------------------------------------------------
# Getters
# --------------------------------------------------------------------------------------------------
def get_project_dir_path() -> Path:
    """Return the outer project directory containing Git and the launchers."""
    return PROJECT_DIR
# --------------------------------------------------------------------------------------------------
def get_app_dir_path() -> Path:
    """Return the internal application directory."""
    return APP_DIR
# --------------------------------------------------------------------------------------------------
def get_src_dir_path() -> Path:
    """Return the source directory."""
    return SRC_DIR
# --------------------------------------------------------------------------------------------------
def get_assets_dir_path() -> Path:
    """Return the assets directory."""
    return ASSETS_DIR
# --------------------------------------------------------------------------------------------------
def get_help_dir_path() -> Path:
    """Return the help assets directory."""
    return HELP_DIR
# --------------------------------------------------------------------------------------------------
def get_help_index_file_path() -> Path:
    """Return the help manual index path."""
    return HELP_INDEX_FILE_PATH
# --------------------------------------------------------------------------------------------------
def get_logs_dir_path() -> Path:
    """Return the logs directory."""
    return LOGS_DIR
# --------------------------------------------------------------------------------------------------
def get_user_data_dir_path() -> Path:
    """Return the local user-data directory."""
    return USER_DATA_DIR
# --------------------------------------------------------------------------------------------------
def get_fake_serial_ports_dir_path() -> Path:
    """Return the directory containing active fake serial-port registrations."""
    return FAKE_SERIAL_PORTS_DIR
# --------------------------------------------------------------------------------------------------
def get_tmp_dir_path() -> Path:
    """Return the temporary-files directory."""
    return TMP_DIR
# --------------------------------------------------------------------------------------------------
def get_pyproject_file_path() -> Path:
    """Return the project metadata file path."""
    return PYPROJECT_FILE_PATH
# --------------------------------------------------------------------------------------------------
def get_uv_lock_file_path() -> Path:
    """Return the uv lock file path."""
    return UV_LOCK_FILE_PATH
# --------------------------------------------------------------------------------------------------
def get_releases_file_path() -> Path:
    """Return the release history file path."""
    return RELEASES_FILE_PATH
# --------------------------------------------------------------------------------------------------
def get_log_file_path() -> Path:
    """Return the rotating log file path."""
    return LOG_FILE_PATH
# --------------------------------------------------------------------------------------------------
def get_icon_file_path() -> Path:
    """Return the optional application icon path."""
    return ICON_FILE_PATH
