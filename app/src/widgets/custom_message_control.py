"""Controls for sending custom messages over active serial connections."""

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.utils.serial_port_monitor import SerialPortMonitor
from src.widgets.help_group_box import HelpGroupBox

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class CustomMessageControl(HelpGroupBox):
    """Broadcast user-entered messages to all open serial ports."""

    def __init__(
        self,
        serial_port_monitor: SerialPortMonitor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Custom Message", "custom-message", parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._serial_port_monitor = serial_port_monitor
        # Message input and send action
        layout = QVBoxLayout(self.content_group_box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self._message_input = QLineEdit(self.content_group_box)
        self._message_input.setPlaceholderText("Enter a message")
        self._message_input.textChanged.connect(self._update_send_button)
        self._message_input.returnPressed.connect(self._send_message)
        layout.addWidget(self._message_input)
        self._send_button = QPushButton("Send", self.content_group_box)
        self._send_button.clicked.connect(self._send_message)
        layout.addWidget(self._send_button)
        self._update_send_button()

    @Slot(str, bool, int)
    def handle_serial_connection_changed(
        self,
        _device: str,
        _connected: bool,
        _baud_rate: int,
    ) -> None:
        """Update message availability after a serial connection changes."""
        self._update_send_button()

    @Slot()
    def _send_message(self) -> None:
        message = self._message_input.text()
        if not message.strip() or not self._serial_port_monitor.connected_devices:
            return
        successful_devices = self._serial_port_monitor.broadcast_write(
            f"{message}\n".encode("utf-8")
        )
        if successful_devices:
            self._message_input.clear()

    @Slot()
    def _update_send_button(self) -> None:
        has_message = bool(self._message_input.text().strip())
        has_connection = bool(self._serial_port_monitor.connected_devices)
        self._send_button.setEnabled(has_message and has_connection)
