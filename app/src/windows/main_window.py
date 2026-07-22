"""Main application window and top-level actions."""

from collections.abc import Callable

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCloseEvent, QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_NAME
from src.utils.gcode_controller import GCodeController
from src.utils.paths import get_pyproject_file_path
from src.utils.releases import get_pyproject_version
from src.utils.serial_port_monitor import SerialPortMonitor
from src.widgets.custom_message_control import CustomMessageControl
from src.widgets.device_serial_port_selector import DeviceSerialPortSelector
from src.widgets.movement_control import MovementControl
from src.widgets.serial_communication_control import SerialCommunicationControl
from src.widgets.terminal_widget import TerminalWidget
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
        self._gcode_controller = GCodeController(self._serial_port_monitor)
        # Shortcut and shutdown state
        self._shortcuts: list[QShortcut] = []
        self._closing_from_action = False
        # Window metadata and initial layout
        self._version = get_pyproject_version(get_pyproject_file_path())
        self.setWindowTitle(APP_NAME)
        self.resize(1_200, 640)
        self._build_content()
        # Application controls and background monitoring
        self._connect_application_signals()
        self._configure_shortcuts()
        self._serial_port_monitor.start()
        self._terminal_widget.append_message(
            "INFO",
            "Application",
            f"Welcome to {APP_NAME}",
        )

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
        separator = QFrame(central_widget)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        # Main actions
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        actions_layout.addStretch(1)
        updates_button = QPushButton("Check for updates", central_widget)
        updates_button.clicked.connect(self._open_release_update_window)
        actions_layout.addWidget(updates_button)
        help_button = QPushButton("Help", central_widget)
        help_button.clicked.connect(self._open_help_window)
        actions_layout.addWidget(help_button)
        actions_layout.addStretch(1)
        layout.addLayout(actions_layout)
        # Main container
        main_container_widget = QWidget(central_widget)
        main_container_layout = QVBoxLayout(main_container_widget)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        main_container_layout.setSpacing(16)
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(16)
        left_controls_widget = QWidget(main_container_widget)
        left_controls_layout = QVBoxLayout(left_controls_widget)
        left_controls_layout.setContentsMargins(0, 0, 0, 0)
        left_controls_layout.setSpacing(16)
        self._device_serial_port_selector = DeviceSerialPortSelector(
            self._serial_port_monitor,
            left_controls_widget,
        )
        left_controls_layout.addWidget(self._device_serial_port_selector)
        self._serial_communication_control = SerialCommunicationControl(
            self._device_serial_port_selector,
            self._serial_port_monitor,
            left_controls_widget,
        )
        left_controls_layout.addWidget(self._serial_communication_control)
        left_controls_layout.addStretch(1)
        controls_layout.addWidget(left_controls_widget, 1)
        self._movement_control = MovementControl(
            self._gcode_controller,
            self._serial_port_monitor,
            main_container_widget,
        )
        controls_layout.addWidget(
            self._movement_control,
            1,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        self._custom_message_control = CustomMessageControl(
            self._serial_port_monitor,
            main_container_widget,
        )
        controls_layout.addWidget(
            self._custom_message_control,
            1,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        main_container_layout.addLayout(controls_layout, 1)
        self._terminal_widget = TerminalWidget(main_container_widget)
        main_container_layout.addWidget(self._terminal_widget)
        layout.addWidget(main_container_widget, 1)
        # Version footer
        version_label = QLabel(f"Version {self._version}", central_widget)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(version_label)

    def _connect_application_signals(self) -> None:
        # Serial-port availability and device configuration
        self._serial_port_monitor.serial_ports_changed.connect(
            self._device_serial_port_selector.set_available_serial_ports
        )
        self._device_serial_port_selector.configuration_changed.connect(
            self._serial_communication_control.handle_device_configuration_changed
        )
        # Serial-connection state
        self._serial_port_monitor.serial_connection_changed.connect(
            self._gcode_controller.handle_serial_connection_changed
        )
        self._serial_port_monitor.serial_connection_changed.connect(
            self._serial_communication_control.handle_serial_connection_changed
        )
        self._serial_port_monitor.serial_connection_changed.connect(
            self._movement_control.handle_serial_connection_changed
        )
        self._serial_port_monitor.serial_connection_changed.connect(
            self._custom_message_control.handle_serial_connection_changed
        )
        self._serial_port_monitor.serial_connection_changed.connect(
            self._handle_serial_connection_changed
        )
        # Terminal events
        self._gcode_controller.command_sent.connect(
            self._handle_serial_message_sent
        )
        self._custom_message_control.message_sent.connect(
            self._handle_serial_message_sent
        )
        self._serial_port_monitor.serial_data_received.connect(
            self._handle_serial_data_received
        )
        self._serial_port_monitor.serial_io_error.connect(
            self._handle_serial_io_error
        )

    @Slot(str, bool, int)
    def _handle_serial_connection_changed(
        self,
        device: str,
        connected: bool,
        baud_rate: int,
    ) -> None:
        if connected:
            message = f"Connected at {baud_rate:,} baud"
        else:
            message = "Disconnected"
        self._terminal_widget.append_message("INFO", device, message)

    @Slot(str, str)
    def _handle_serial_message_sent(self, device: str, message: str) -> None:
        self._terminal_widget.append_message("TX", device, message)

    @Slot(str, str)
    def _handle_serial_data_received(self, device: str, message: str) -> None:
        self._terminal_widget.append_message("RX", device, message)

    @Slot(str, str)
    def _handle_serial_io_error(self, device: str, error_message: str) -> None:
        self._terminal_widget.append_message("ERROR", device, error_message)

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
