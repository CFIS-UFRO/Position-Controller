"""Release update dialog and installation action."""

import sys
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_NAME, RESTART_EXIT_CODE
from src.utils.logging import logger
from src.utils.paths import get_project_dir_path
from src.utils.releases import ReleaseUpdate, install_release_update
from src.widgets.release_update_details import ReleaseUpdateDetails

# --------------------------------------------------------------------------------------------------
# Dialog
# --------------------------------------------------------------------------------------------------
class ReleaseUpdateWindow(QDialog):
    """Display the latest release and install it when appropriate."""

    def __init__(
        self,
        release_update: ReleaseUpdate,
        restart_callback: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._release_update = release_update
        self._restart_callback = restart_callback
        self._updates_disabled_by_git = (get_project_dir_path() / ".git").exists()
        self._can_update = release_update.is_update_available and not self._updates_disabled_by_git
        self.setWindowTitle("Updates")
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(ReleaseUpdateDetails(release_update, self), 1)
        actions_layout = QHBoxLayout()
        actions_layout.addStretch(1)
        self._update_button = QPushButton("Install update", self)
        self._update_button.setEnabled(self._can_update)
        self._update_button.clicked.connect(self._handle_update_clicked)
        actions_layout.addWidget(self._update_button, 0, Qt.AlignCenter)
        close_button = QPushButton("Close", self)
        close_button.setDefault(not self._can_update)
        close_button.clicked.connect(self.accept)
        actions_layout.addWidget(close_button, 0, Qt.AlignCenter)
        actions_layout.addStretch(1)
        layout.addLayout(actions_layout)
        if self._updates_disabled_by_git:
            git_warning_label = QLabel(
                "Git repository detected. In-app installation is disabled for development checkouts.",
                self,
            )
            git_warning_label.setAlignment(Qt.AlignCenter)
            git_warning_label.setWordWrap(True)
            git_warning_label.setStyleSheet("color: #c62828;")
            layout.addWidget(git_warning_label)

    def show_window(self) -> None:
        """Show, raise, and activate the update dialog."""
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        if sys.platform != "darwin":
            self.activateWindow()

    def _handle_update_clicked(self) -> None:
        answer = QMessageBox.question(
            self,
            "Install update",
            f"Install {APP_NAME} {self._release_update.latest_version} and restart the application?",
        )
        if answer != QMessageBox.Yes:
            return
        self._update_button.setEnabled(False)
        self._update_button.setText("Updating...")
        QApplication.processEvents()
        try:
            install_release_update(self._release_update)
        except Exception as exc:
            logger.exception("Update installation failed")
            self._update_button.setText("Install update")
            self._update_button.setEnabled(self._can_update)
            QMessageBox.warning(self, "Update failed", str(exc))
            return
        if self._restart_callback is not None:
            self._restart_callback()
            return
        app = QApplication.instance()
        if app is not None:
            app.exit(RESTART_EXIT_CODE)
