"""Device serial-port selection widget."""

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QWidget,
)
from serial.tools.list_ports_common import ListPortInfo

from src.utils.serial_port_monitor import SerialPortMonitor

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class DeviceSerialPortSelector(QGroupBox):
    """Select a unique serial port for each configured device."""

    configuration_changed = Signal()

    MIN_DEVICE_COUNT = 1
    MAX_DEVICE_COUNT = 8
    BAUD_RATES = (9_600, 19_200, 38_400, 57_600, 115_200, 250_000)
    DEFAULT_BAUD_RATE = 115_200

    def __init__(
        self,
        serial_port_monitor: SerialPortMonitor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Devices Selection", parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Serial-port and per-row selection state
        self._available_serial_ports = serial_port_monitor.serial_ports
        self._device_labels: list[QLabel] = []
        self._device_separators: list[QLabel] = []
        self._device_selectors: list[QComboBox] = []
        self._baud_rate_selectors: list[QComboBox] = []
        self._remembered_serial_ports: list[ListPortInfo | None] = []
        self._updating_selectors = False
        self._selection_enabled = True
        self._last_emitted_configuration: tuple[
            tuple[str | None, ...],
            tuple[int | None, ...],
            tuple[str, ...],
        ] | None = None
        # Label-and-control grid
        self._grid_layout = QGridLayout(self)
        self._grid_layout.setContentsMargins(8, 8, 8, 8)
        self._grid_layout.setHorizontalSpacing(6)
        self._grid_layout.setVerticalSpacing(8)
        self._grid_layout.setColumnStretch(2, 1)
        self._grid_layout.addWidget(QLabel("Number of devices", self), 0, 0)
        self._grid_layout.addWidget(QLabel(":", self), 0, 1)
        self._device_count_selector = QSpinBox(self)
        self._device_count_selector.setRange(self.MIN_DEVICE_COUNT, self.MAX_DEVICE_COUNT)
        self._device_count_selector.setValue(self.MIN_DEVICE_COUNT)
        self._device_count_selector.valueChanged.connect(self._set_device_count)
        self._grid_layout.addWidget(self._device_count_selector, 0, 2, 1, 2)
        self._grid_layout.addWidget(QLabel("Serial port", self), 1, 2)
        self._grid_layout.addWidget(QLabel("Baud rate", self), 1, 3)
        self._set_device_count(self._device_count_selector.value())

    def get_selected_devices(self) -> list[str | None]:
        """Return the currently selected serial device names in row order."""
        selected_devices: list[str | None] = []
        for selector in self._device_selectors:
            device = selector.currentData()
            selected_devices.append(device if isinstance(device, str) else None)
        return selected_devices

    def get_selected_device_baud_rates(self) -> dict[str, int]:
        """Return each selected serial device and its configured baud rate."""
        device_baud_rates: dict[str, int] = {}
        for device_selector, baud_rate_selector in zip(
            self._device_selectors,
            self._baud_rate_selectors,
            strict=True,
        ):
            device = device_selector.currentData()
            baud_rate = baud_rate_selector.currentData()
            if (
                isinstance(device, str)
                and isinstance(baud_rate, int)
                and not isinstance(baud_rate, bool)
            ):
                device_baud_rates[device] = baud_rate
        return device_baud_rates

    def set_selection_enabled(self, enabled: bool) -> None:
        """Enable or disable the device count, serial-port, and baud selectors."""
        self._selection_enabled = enabled
        self._device_count_selector.setEnabled(enabled)
        for selector in self._device_selectors:
            selector.setEnabled(enabled)
        for selector in self._baud_rate_selectors:
            selector.setEnabled(enabled)

    def _set_device_count(self, device_count: int) -> None:
        # Grow or shrink from the end so existing row assignments remain stable.
        while len(self._device_labels) < device_count:
            self._add_device_row()
        while len(self._device_labels) > device_count:
            self._remove_device_row()
        self._rebuild_device_selectors()

    def _add_device_row(self) -> None:
        # Build one labeled selector and initialize its remembered assignment.
        row_number = len(self._device_labels) + 1
        label = QLabel(f"Device {row_number}", self)
        separator = QLabel(":", self)
        selector = QComboBox(self)
        selector.addItem("None")
        selector.setEnabled(self._selection_enabled)
        selector.currentIndexChanged.connect(self._handle_device_selection_changed)
        baud_rate_selector = QComboBox(self)
        for baud_rate in self.BAUD_RATES:
            baud_rate_selector.addItem(f"{baud_rate:,}", baud_rate)
        baud_rate_selector.setCurrentIndex(
            baud_rate_selector.findData(self.DEFAULT_BAUD_RATE)
        )
        baud_rate_selector.setEnabled(self._selection_enabled)
        baud_rate_selector.currentIndexChanged.connect(
            self._handle_baud_rate_selection_changed
        )
        grid_row = row_number + 1
        self._grid_layout.addWidget(label, grid_row, 0)
        self._grid_layout.addWidget(separator, grid_row, 1)
        self._grid_layout.addWidget(selector, grid_row, 2)
        self._grid_layout.addWidget(baud_rate_selector, grid_row, 3)
        self._device_labels.append(label)
        self._device_separators.append(separator)
        self._device_selectors.append(selector)
        self._baud_rate_selectors.append(baud_rate_selector)
        self._remembered_serial_ports.append(None)

    def _remove_device_row(self) -> None:
        # Removing a row also discards its current and remembered assignment.
        label = self._device_labels.pop()
        separator = self._device_separators.pop()
        selector = self._device_selectors.pop()
        baud_rate_selector = self._baud_rate_selectors.pop()
        self._remembered_serial_ports.pop()
        self._grid_layout.removeWidget(label)
        self._grid_layout.removeWidget(separator)
        self._grid_layout.removeWidget(selector)
        self._grid_layout.removeWidget(baud_rate_selector)
        label.deleteLater()
        separator.deleteLater()
        selector.deleteLater()
        baud_rate_selector.deleteLater()

    @Slot(list)
    def set_available_serial_ports(self, serial_ports: list[object]) -> None:
        """Update the available serial ports and rebuild the device selectors."""
        # Accept only the monitor's expected list payload and known port objects.
        self._available_serial_ports = [
            port for port in serial_ports if isinstance(port, ListPortInfo)
        ]
        self._rebuild_device_selectors()

    def _handle_device_selection_changed(self, _index: int) -> None:
        # Ignore index changes caused while dropdown options are being rebuilt.
        if self._updating_selectors:
            return
        selector = self.sender()
        if not isinstance(selector, QComboBox):
            return
        try:
            row_index = self._device_selectors.index(selector)
        except ValueError:
            return
        # A user-selected port becomes the reconnection target; None clears it.
        device = selector.currentData()
        self._remembered_serial_ports[row_index] = next(
            (port for port in self._available_serial_ports if port.device == device),
            None,
        )
        self._rebuild_device_selectors()

    def _handle_baud_rate_selection_changed(self, _index: int) -> None:
        self._emit_configuration_changed()

    def _rebuild_device_selectors(self) -> None:
        # Restore remembered ports only when available and not claimed by an earlier row.
        available_ports = {port.device: port for port in self._available_serial_ports}
        selected_devices: list[str | None] = []
        claimed_devices: set[str] = set()
        for row_index, remembered_port in enumerate(self._remembered_serial_ports):
            remembered_device = remembered_port.device if remembered_port is not None else None
            if (
                remembered_device is not None
                and remembered_device in available_ports
                and remembered_device not in claimed_devices
            ):
                selected_devices.append(remembered_device)
                claimed_devices.add(remembered_device)
                self._remembered_serial_ports[row_index] = available_ports[remembered_device]
            else:
                selected_devices.append(None)
        # Rebuild each dropdown without treating automatic selections as user input.
        self._updating_selectors = True
        try:
            for row_index, selector in enumerate(self._device_selectors):
                selected_device = selected_devices[row_index]
                remembered_port = self._remembered_serial_ports[row_index]
                reserved_devices = claimed_devices.copy()
                if selected_device is not None:
                    reserved_devices.remove(selected_device)
                selector.clear()
                selector.addItem("None")
                # Hide ports reserved by other rows while retaining this row's selection.
                for port in self._available_serial_ports:
                    if port.device in reserved_devices:
                        continue
                    selector.addItem(
                        SerialPortMonitor.format_serial_port(port),
                        port.device,
                    )
                if selected_device is not None:
                    selector.setCurrentIndex(selector.findData(selected_device))
                elif remembered_port is not None:
                    selector.addItem(
                        SerialPortMonitor.format_serial_port(
                            remembered_port,
                            disconnected=True,
                        ),
                        remembered_port.device,
                    )
                    selector.setCurrentIndex(selector.count() - 1)
                else:
                    selector.setCurrentIndex(0)
        finally:
            self._updating_selectors = False
        self._emit_configuration_changed()

    def _emit_configuration_changed(self) -> None:
        baud_rates: list[int | None] = []
        for selector in self._baud_rate_selectors:
            baud_rate = selector.currentData()
            baud_rates.append(
                baud_rate
                if isinstance(baud_rate, int) and not isinstance(baud_rate, bool)
                else None
            )
        configuration = (
            tuple(self.get_selected_devices()),
            tuple(baud_rates),
            tuple(port.device for port in self._available_serial_ports),
        )
        if configuration == self._last_emitted_configuration:
            return
        self._last_emitted_configuration = configuration
        self.configuration_changed.emit()
