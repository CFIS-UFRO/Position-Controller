"""Serial-port monitoring helpers."""

import json
import os

from PySide6.QtCore import QObject, Signal, QTimer
from serial import Serial, SerialException
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo

from src.utils.logging import logger
from src.utils.paths import get_fake_serial_ports_dir_path

# --------------------------------------------------------------------------------------------------
# Port monitoring
# --------------------------------------------------------------------------------------------------
class SerialPortMonitor(QObject):
    """Track available serial ports and own their open connections."""

    serial_ports_changed = Signal(object)
    serial_connection_closed_by_disconnection = Signal(str)

    SCAN_INTERVAL_MS = 5_000

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._serial_ports: list[ListPortInfo] = []
        self._serial_connections: dict[str, Serial] = {}
        self._connection_errors: dict[str, str] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(self.SCAN_INTERVAL_MS)
        self._timer.timeout.connect(self._refresh)

    @property
    def serial_ports(self) -> list[ListPortInfo]:
        """Return a copy of the latest available serial-port list."""
        return self._serial_ports.copy()

    @property
    def is_running(self) -> bool:
        """Return whether serial-port monitoring is active."""
        return self._timer.isActive()

    def is_device_available(self, device: str) -> bool:
        """Return whether a serial device is currently available."""
        return any(port.device == device for port in self._serial_ports)

    def is_device_connected(self, device: str) -> bool:
        """Return whether a serial device has an open connection."""
        connection = self._serial_connections.get(device)
        return connection is not None and connection.is_open

    def get_connection_error(self, device: str) -> str | None:
        """Return the most recent connection error for a serial device."""
        return self._connection_errors.get(device)

    def open_connection(self, device: str) -> bool:
        """Open and store a serial connection, returning whether it is open."""
        if not self.is_device_available(device):
            self._connection_errors.pop(device, None)
            return False
        if self.is_device_connected(device):
            self._connection_errors.pop(device, None)
            return True
        self.close_connection(device)
        try:
            self._serial_connections[device] = Serial(port=device)
        except (OSError, SerialException) as error:
            self._connection_errors[device] = str(error)
            logger.error(f"Could not open serial port {device}: {error}")
            return False
        self._connection_errors.pop(device, None)
        logger.info(f"Serial port opened: {device}")
        return True

    def close_connection(self, device: str) -> bool:
        """Close and forget a serial connection, returning whether one existed."""
        connection = self._serial_connections.pop(device, None)
        if connection is None:
            return False
        try:
            connection.close()
        except (OSError, SerialException) as error:
            logger.warning(f"Could not close serial port {device}: {error}")
        else:
            logger.info(f"Serial port closed: {device}")
        return True

    def close_all_connections(self) -> bool:
        """Close every stored serial connection and clear connection errors."""
        had_connections = bool(self._serial_connections)
        for device in list(self._serial_connections):
            self.close_connection(device)
        self._connection_errors.clear()
        return had_connections

    def synchronize_connections(self, devices: list[str]) -> None:
        """Keep open connections aligned with the requested serial devices."""
        requested_devices = set(devices)
        for device in list(self._serial_connections):
            if device not in requested_devices or not self.is_device_available(device):
                self.close_connection(device)
        for device in devices:
            if not self.is_device_available(device):
                self._connection_errors.pop(device, None)
                continue
            self.open_connection(device)

    def start(self) -> bool:
        """Start monitoring and return whether monitoring was started."""
        if self.is_running:
            return False
        self._refresh()
        self._timer.start()
        return True

    def stop(self) -> bool:
        """Stop monitoring and return whether monitoring was stopped."""
        if not self.is_running:
            return False
        self._timer.stop()
        return True

    def _refresh(self) -> None:
        serial_ports = self.get_available_serial_ports()
        previous_ports = {port.device: port for port in self._serial_ports}
        current_ports = {port.device: port for port in serial_ports}
        connected_devices = sorted(current_ports.keys() - previous_ports.keys())
        disconnected_devices = sorted(previous_ports.keys() - current_ports.keys())
        for device in connected_devices:
            logger.info(f"Serial port connected: {self._format_serial_port(current_ports[device])}")
        for device in disconnected_devices:
            logger.info(f"Serial port disconnected: {self._format_serial_port(previous_ports[device])}")
        self._serial_ports = serial_ports
        for device in disconnected_devices:
            was_connected = self.is_device_connected(device)
            self.close_connection(device)
            self._connection_errors.pop(device, None)
            if was_connected:
                self.serial_connection_closed_by_disconnection.emit(device)
        if previous_ports.keys() != current_ports.keys():
            self.serial_ports_changed.emit(self.serial_ports)

    @staticmethod
    def get_available_serial_ports() -> list[ListPortInfo]:
        """Return hardware and registered fake serial ports."""
        serial_ports = {port.device: port for port in list_ports.comports()}
        for port in SerialPortMonitor._get_registered_fake_serial_ports():
            serial_ports.setdefault(port.device, port)
        return sorted(serial_ports.values())

    @staticmethod
    def _get_registered_fake_serial_ports() -> list[ListPortInfo]:
        fake_serial_ports: list[ListPortInfo] = []
        registration_dir_path = get_fake_serial_ports_dir_path()
        if not registration_dir_path.is_dir():
            return fake_serial_ports
        for registration_file_path in sorted(registration_dir_path.glob("*.json")):
            try:
                registration = json.loads(registration_file_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(registration, dict):
                continue
            process_id = registration.get("pid")
            device = registration.get("device")
            description = registration.get("description")
            if (
                not isinstance(process_id, int)
                or isinstance(process_id, bool)
                or process_id <= 0
                or not isinstance(device, str)
                or not device
                or not isinstance(description, str)
                or not description
                or not os.path.exists(device)
                or not SerialPortMonitor._is_process_running(process_id)
            ):
                continue
            port = ListPortInfo(device)
            port.description = description
            fake_serial_ports.append(port)
        return fake_serial_ports

    @staticmethod
    def _is_process_running(process_id: int) -> bool:
        try:
            os.kill(process_id, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    @staticmethod
    def _format_serial_port(port: ListPortInfo) -> str:
        if port.description and port.description != "n/a":
            return f"{port.description} ({port.device})"
        return port.device
