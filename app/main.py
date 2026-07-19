"""Position Controller application entry point."""

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.config import APP_NAME, ORGANIZATION_NAME, RESTART_EXIT_CODE
from src.utils.logging import init_logging, logger
from src.utils.paths import get_icon_file_path
from src.utils.tmp import clean_tmp_dir
from src.windows.main_window import MainWindow

# --------------------------------------------------------------------------------------------------
# Application lifecycle
# --------------------------------------------------------------------------------------------------
def restart_app(app: QApplication) -> None:
    """Request a launcher-level application restart."""
    logger.info("Restart requested")
    app.exit(RESTART_EXIT_CODE)
# --------------------------------------------------------------------------------------------------
def quit_app(app: QApplication) -> None:
    """Quit the current application process."""
    logger.info("Quit requested")
    app.quit()
# --------------------------------------------------------------------------------------------------
def about_to_quit() -> None:
    """Record application shutdown."""
    logger.info(f"Closing {APP_NAME}...")
# --------------------------------------------------------------------------------------------------
def main() -> int:
    """Initialize and run the Qt application."""
    init_logging()
    clean_tmp_dir()
    logger.info(f"Starting {APP_NAME}...")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)
    icon_file_path = get_icon_file_path()
    if icon_file_path.is_file():
        app.setWindowIcon(QIcon(str(icon_file_path)))
    window = MainWindow(
        restart_callback=lambda: restart_app(app),
        quit_callback=lambda: quit_app(app),
    )
    app.aboutToQuit.connect(about_to_quit)
    window.show()
    window.center_on_screen()
    return app.exec()

# --------------------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    raise SystemExit(main())
