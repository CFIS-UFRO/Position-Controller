"""Serial communication controls and connection-status display."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHeaderView,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.utils.logging import logger
from src.utils.serial_port_monitor import SerialPortMonitor
from src.widgets.device_serial_port_selector import DeviceSerialPortSelector

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class SerialCommunicationControl(QGroupBox):
    """Open selected serial ports and display their communication status."""

    _DISCONNECTED_BACKGROUND = QColor("#e0e0e0")
    _DISCONNECTED_FOREGROUND = QColor("#424242")
    _ERROR_BACKGROUND = QColor("#ffcdd2")
    _ERROR_FOREGROUND = QColor("#b71c1c")
    _CONNECTED_BACKGROUND = QColor("#c8e6c9")
    _CONNECTED_FOREGROUND = QColor("#1b5e20")

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
        # Status table and communication control
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        self._status_table = QTableWidget(0, 2, self)
        self._status_table.setHorizontalHeaderLabels(["Serial port", "Status"])
        self._status_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._status_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._status_table.verticalHeader().setVisible(False)
        horizontal_header = self._status_table.horizontalHeader()
        horizontal_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        horizontal_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._status_table)
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
        self._refresh_status_table()

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
        self._refresh_status_table()
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
        self._refresh_status_table(selected_devices)

    def _handle_serial_ports_changed(self, _serial_ports: object) -> None:
        selected_devices = self._get_selected_devices()
        if self._communication_active:
            self._synchronize_connections(selected_devices)
            return
        self._refresh_status_table(selected_devices)

    def _synchronize_connections(self, selected_devices: list[str]) -> None:
        self._serial_port_monitor.synchronize_connections(selected_devices)
        self._refresh_status_table(selected_devices)

    def _refresh_status_table(self, selected_devices: list[str] | None = None) -> None:
        if selected_devices is None:
            selected_devices = self._get_selected_devices()
        self._status_table.clearSpans()
        if not selected_devices:
            self._status_table.setRowCount(1)
            empty_item = QTableWidgetItem("No serial ports selected")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setForeground(self._DISCONNECTED_FOREGROUND)
            self._status_table.setItem(0, 0, empty_item)
            self._status_table.setSpan(0, 0, 1, 2)
            self._resize_status_table(1)
            self._communication_button.setEnabled(False)
            return
        self._status_table.setRowCount(len(selected_devices))
        for row_index, device in enumerate(selected_devices):
            device_item = QTableWidgetItem(device)
            status, background, foreground, tooltip = self._get_device_status(device)
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setBackground(background)
            status_item.setForeground(foreground)
            if tooltip:
                status_item.setToolTip(tooltip)
            self._status_table.setItem(row_index, 0, device_item)
            self._status_table.setItem(row_index, 1, status_item)
        self._resize_status_table(len(selected_devices))
        self._communication_button.setEnabled(
            self._communication_active or bool(selected_devices)
        )

    def _resize_status_table(self, row_count: int) -> None:
        table_height = (
            self._status_table.horizontalHeader().height()
            + self._status_table.verticalHeader().defaultSectionSize() * row_count
            + self._status_table.frameWidth() * 2
        )
        self._status_table.setFixedHeight(table_height)

    def _get_device_status(self, device: str) -> tuple[str, QColor, QColor, str]:
        if not self._communication_active:
            return (
                "Disconnected",
                self._DISCONNECTED_BACKGROUND,
                self._DISCONNECTED_FOREGROUND,
                "Communication has not been started.",
            )
        if not self._serial_port_monitor.is_device_available(device):
            return (
                "Disconnected",
                self._ERROR_BACKGROUND,
                self._ERROR_FOREGROUND,
                "The selected serial port is not available.",
            )
        if self._serial_port_monitor.is_device_connected(device):
            return (
                "Connected",
                self._CONNECTED_BACKGROUND,
                self._CONNECTED_FOREGROUND,
                "The serial port is open and available.",
            )
        return (
            "Not working",
            self._ERROR_BACKGROUND,
            self._ERROR_FOREGROUND,
            self._serial_port_monitor.get_connection_error(device)
            or "The serial port could not be opened.",
        )

    def _get_selected_devices(self) -> list[str]:
        return [
            device
            for device in self._device_selector.get_selected_devices()
            if device is not None
        ]
