"""Serial communication controls and connection-status display."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.utils.logging import logger
from src.utils.serial_port_monitor import SerialPortMonitor
from src.widgets.badge_widget import BadgeWidget
from src.widgets.device_serial_port_selector import DeviceSerialPortSelector

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class SerialCommunicationControl(QGroupBox):
    """Open selected serial ports and display their communication status."""

    def __init__(
        self,
        device_selector: DeviceSerialPortSelector,
        serial_port_monitor: SerialPortMonitor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Serial Communication", parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._device_selector = device_selector
        self._serial_port_monitor = serial_port_monitor
        self._communication_active = False
        # Status display and communication control
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        self._status_widget = QWidget(self)
        self._status_layout = QGridLayout(self._status_widget)
        self._status_layout.setContentsMargins(0, 0, 0, 0)
        self._status_layout.setHorizontalSpacing(6)
        self._status_layout.setVerticalSpacing(8)
        self._status_layout.setColumnStretch(2, 1)
        layout.addWidget(self._status_widget)
        self._communication_button = QPushButton("Start", self)
        self._communication_button.clicked.connect(self._toggle_communication)
        layout.addWidget(
            self._communication_button,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        # Keep status rows synchronized with selection and port availability changes.
        self._device_selector.selected_devices_changed.connect(
            self._handle_selected_devices_changed
        )
        self._serial_port_monitor.serial_ports_changed.connect(
            self._handle_serial_ports_changed
        )
        self._serial_port_monitor.serial_connection_changed.connect(
            self._handle_serial_connection_changed
        )
        self._refresh_status_display()

    @property
    def is_communication_active(self) -> bool:
        """Return whether serial communication has been started."""
        return self._communication_active

    def stop_communication(self) -> bool:
        """Close all serial ports and return whether communication was stopped."""
        if not self._communication_active:
            return False
        self._communication_active = False
        self._serial_port_monitor.close_all_connections()
        self._device_selector.set_selection_enabled(True)
        self._communication_button.setText("Start")
        self._refresh_status_display()
        logger.info("Serial communication stopped")
        return True

    def _toggle_communication(self) -> None:
        if self._communication_active:
            self.stop_communication()
            return
        selected_devices = self._get_selected_devices()
        if not selected_devices:
            return
        self._communication_active = True
        self._device_selector.set_selection_enabled(False)
        self._communication_button.setText("Stop")
        self._synchronize_connections(selected_devices)
        logger.info("Serial communication started")

    def _handle_selected_devices_changed(self, _selected_devices: object) -> None:
        selected_devices = self._get_selected_devices()
        if self._communication_active:
            self._synchronize_connections(selected_devices)
            return
        self._refresh_status_display(selected_devices)

    def _handle_serial_ports_changed(self, _serial_ports: object) -> None:
        selected_devices = self._get_selected_devices()
        if self._communication_active:
            self._synchronize_connections(selected_devices)
            return
        self._refresh_status_display(selected_devices)

    def _handle_serial_connection_changed(
        self,
        _device: str,
        _connected: bool,
        _baud_rate: int,
    ) -> None:
        self._refresh_status_display()

    def _synchronize_connections(self, selected_devices: list[str]) -> None:
        self._serial_port_monitor.synchronize_connections(
            self._device_selector.get_selected_device_baud_rates()
        )
        self._refresh_status_display(selected_devices)

    def _refresh_status_display(
        self,
        selected_devices: list[str] | None = None,
    ) -> None:
        if selected_devices is None:
            selected_devices = self._get_selected_devices()
        self._clear_status_display()
        self._status_layout.addWidget(QLabel("Serial port", self._status_widget), 0, 0)
        self._status_layout.addWidget(QLabel("Status", self._status_widget), 0, 2)
        header_separator = QFrame(self._status_widget)
        header_separator.setFrameShape(QFrame.Shape.HLine)
        header_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self._status_layout.addWidget(header_separator, 1, 0, 1, 3)
        if not selected_devices:
            empty_label = QLabel("No serial ports selected", self._status_widget)
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._status_layout.addWidget(
                empty_label,
                2,
                0,
                1,
                3,
            )
            self._communication_button.setEnabled(False)
            return
        serial_ports_by_device = {
            port.device: port for port in self._serial_port_monitor.serial_ports
        }
        for row_index, device in enumerate(selected_devices, start=2):
            status, color, tooltip = self._get_device_status(device)
            serial_port = serial_ports_by_device.get(device)
            label_text = (
                SerialPortMonitor.format_serial_port(serial_port)
                if serial_port is not None
                else device
            )
            self._add_status_row(row_index, label_text, status, color, tooltip)
        self._communication_button.setEnabled(
            self._communication_active or bool(selected_devices)
        )

    def _add_status_row(
        self,
        row_index: int,
        label_text: str,
        status: str,
        color: str,
        tooltip: str,
    ) -> None:
        label = QLabel(label_text, self._status_widget)
        separator = QLabel(":", self._status_widget)
        status_badge = BadgeWidget(status, color, self._status_widget)
        status_badge.setMinimumWidth(100)
        if tooltip:
            status_badge.setToolTip(tooltip)
        self._status_layout.addWidget(label, row_index, 0)
        self._status_layout.addWidget(separator, row_index, 1)
        self._status_layout.addWidget(status_badge, row_index, 2)

    def _clear_status_display(self) -> None:
        while self._status_layout.count():
            layout_item = self._status_layout.takeAt(0)
            if layout_item is None:
                continue
            widget = layout_item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _get_device_status(self, device: str) -> tuple[str, str, str]:
        if not self._communication_active:
            return (
                "Disconnected",
                "gray",
                "Communication has not been started.",
            )
        if not self._serial_port_monitor.is_device_available(device):
            return (
                "Disconnected",
                "red",
                "The selected serial port is not available.",
            )
        if self._serial_port_monitor.is_device_connected(device):
            return (
                "Connected",
                "green",
                "The serial port is open and available.",
            )
        return (
            "Not working",
            "red",
            self._serial_port_monitor.get_connection_error(device)
            or "The serial port could not be opened.",
        )

    def _get_selected_devices(self) -> list[str]:
        return [
            device
            for device in self._device_selector.get_selected_devices()
            if device is not None
        ]
