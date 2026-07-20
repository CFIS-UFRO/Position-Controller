"""Main application window and top-level actions."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_NAME
from src.utils.paths import get_pyproject_file_path
from src.utils.releases import get_pyproject_version
from src.utils.serial_port_monitor import SerialPortMonitor
from src.widgets.device_serial_port_selector import DeviceSerialPortSelector
from src.widgets.serial_communication_control import SerialCommunicationControl
from src.windows.help_window import HelpWindow
from src.windows.release_update_window import ReleaseUpdateWindow

# --------------------------------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------------------------------
class MainWindow(QMainWindow):
    """Main application window and reusable application shell."""

    def __init__(
        self,
        restart_callback: Callable[[], None] | None = None,
        quit_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        # Application lifecycle callbacks
        self._restart_callback = restart_callback
        self._quit_callback = quit_callback
        # Child windows and background services
        self._help_window: HelpWindow | None = None
        self._release_update_window: ReleaseUpdateWindow | None = None
        self._serial_port_monitor = SerialPortMonitor(self)
        # Shortcut and shutdown state
        self._shortcuts: list[QShortcut] = []
        self._closing_from_action = False
        # Window metadata and initial layout
        self._version = get_pyproject_version(get_pyproject_file_path())
        self.setWindowTitle(APP_NAME)
        self.resize(960, 640)
        self._build_content()
        # Application controls and background monitoring
        self._configure_shortcuts()
        self._serial_port_monitor.start()

    def _build_content(self) -> None:
        # Central container and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)
        # Application title
        title_label = QLabel(APP_NAME, central_widget)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 26px; font-weight: 600;")
        layout.addWidget(title_label)
        # Device connections
        self._device_serial_port_selector = DeviceSerialPortSelector(
            self._serial_port_monitor,
            central_widget,
        )
        layout.addWidget(self._device_serial_port_selector)
        self._serial_communication_control = SerialCommunicationControl(
            self._device_serial_port_selector,
            self._serial_port_monitor,
            central_widget,
        )
        layout.addWidget(self._serial_communication_control)
        # Main actions
        updates_button = QPushButton("Check for updates", central_widget)
        updates_button.clicked.connect(self._open_release_update_window)
        layout.addWidget(updates_button, alignment=Qt.AlignmentFlag.AlignCenter)
        help_button = QPushButton("Help", central_widget)
        help_button.clicked.connect(self._open_help_window)
        layout.addWidget(help_button, alignment=Qt.AlignmentFlag.AlignCenter)
        # Version footer
        layout.addStretch(1)
        version_label = QLabel(f"Version {self._version}", central_widget)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(version_label)

    def _configure_shortcuts(self) -> None:
        """Configure application-level restart and quit shortcuts."""
        if self._restart_callback is not None:
            for sequence in ("Ctrl+R", "Meta+R"):
                shortcut = QShortcut(QKeySequence(sequence), self)
                shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
                shortcut.activated.connect(self._restart_callback)
                self._shortcuts.append(shortcut)
        for sequence in ("Ctrl+Q", "Meta+Q"):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(self._quit)
            self._shortcuts.append(shortcut)

    def center_on_screen(self) -> None:
        """Center the window on the screen containing the mouse cursor."""
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        window_frame = self.frameGeometry()
        window_frame.moveCenter(screen.availableGeometry().center())
        self.move(window_frame.topLeft())

    def check_for_updates_on_startup(self) -> None:
        """Check for a new release without showing current-version or error dialogs."""
        self._get_release_update_window().check_for_updates_on_startup()

    def stop_serial_port_monitor(self) -> None:
        """Stop monitoring for serial-port changes."""
        self._serial_port_monitor.stop()

    def stop_serial_communication(self) -> None:
        """Close all active serial-port connections."""
        self._serial_communication_control.stop_communication()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Route window-manager closes through the configured quit callback."""
        if self._quit_callback is None or self._closing_from_action:
            event.accept()
            return
        event.ignore()
        self._closing_from_action = True
        self._quit_callback()

    def _quit(self) -> None:
        self._closing_from_action = True
        if self._quit_callback is not None:
            self._quit_callback()
            return
        self.close()

    def _open_help_window(self) -> None:
        if self._help_window is None:
            self._help_window = HelpWindow(initial_manual_id="getting-started", parent=self)
        self._help_window.show_window()

    def _open_release_update_window(self) -> None:
        self._get_release_update_window().check_for_updates()

    def _get_release_update_window(self) -> ReleaseUpdateWindow:
        if self._release_update_window is None:
            self._release_update_window = ReleaseUpdateWindow(
                restart_callback=self._restart_callback,
                parent=self,
            )
        return self._release_update_window
