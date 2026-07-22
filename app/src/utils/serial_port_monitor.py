"""Serial-port monitoring helpers."""

import json
import os

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot, QTimer
from serial import Serial, SerialException, SerialTimeoutException
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo

from src.utils.logging import logger
from src.utils.paths import get_fake_serial_ports_dir_path

# --------------------------------------------------------------------------------------------------
# Serial reader
# --------------------------------------------------------------------------------------------------
class _SerialReaderThread(QThread):
    """Read line-oriented serial data without blocking the application thread."""

    READ_CHUNK_SIZE = 4_096

    data_received = Signal(str, str)
    failed = Signal(str, str)

    def __init__(
        self,
        device: str,
        connection: Serial,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._device = device
        self._connection = connection

    def run(self) -> None:
        pending_data = bytearray()
        while not self.isInterruptionRequested():
            try:
                bytes_to_read = min(
                    max(self._connection.in_waiting, 1),
                    self.READ_CHUNK_SIZE,
                )
                received_data = self._connection.read(bytes_to_read)
            except (OSError, SerialException, TypeError) as error:
                if not self.isInterruptionRequested():
                    self.failed.emit(self._device, str(error))
                return
            if not received_data:
                continue
            pending_data.extend(received_data)
            lines = pending_data.split(b"\n")
            pending_data = lines.pop()
            for line in lines:
                line = line.rstrip(b"\r")
                message = line.decode("utf-8", errors="replace")
                self.data_received.emit(self._device, message)

# --------------------------------------------------------------------------------------------------
# Port monitoring
# --------------------------------------------------------------------------------------------------
class SerialPortMonitor(QObject):
    """Track available serial ports and own their open connections."""

    serial_ports_changed = Signal(list)
    serial_connection_changed = Signal(str, bool, int)
    serial_data_received = Signal(str, str)
    serial_io_error = Signal(str, str)

    SCAN_INTERVAL_MS = 5_000
    READ_TIMEOUT_SECONDS = 0.1
    WRITE_TIMEOUT_SECONDS = 1.0
    READER_STOP_TIMEOUT_MS = 1_000

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._serial_ports: list[ListPortInfo] = []
        self._serial_connections: dict[str, Serial] = {}
        self._serial_readers: dict[str, _SerialReaderThread] = {}
        self._connection_errors: dict[str, str] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(self.SCAN_INTERVAL_MS)
        self._timer.timeout.connect(self._refresh)

    @property
    def serial_ports(self) -> list[ListPortInfo]:
        """Return a copy of the latest available serial-port list."""
        return self._serial_ports.copy()

    @property
    def connected_devices(self) -> list[str]:
        """Return the device names of all currently open serial connections."""
        return [
            device
            for device, connection in self._serial_connections.items()
            if connection.is_open
        ]

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

    def open_connection(self, device: str, baud_rate: int) -> bool:
        """Open and store a serial connection, returning whether it is open."""
        if (
            not isinstance(baud_rate, int)
            or isinstance(baud_rate, bool)
            or baud_rate <= 0
        ):
            raise ValueError("Baud rate must be a positive integer.")
        if not self.is_device_available(device):
            self._connection_errors.pop(device, None)
            return False
        connection = self._serial_connections.get(device)
        if (
            connection is not None
            and connection.is_open
            and connection.baudrate == baud_rate
        ):
            self._connection_errors.pop(device, None)
            return True
        self.close_connection(device)
        try:
            connection = Serial(
                port=device,
                baudrate=baud_rate,
                timeout=self.READ_TIMEOUT_SECONDS,
                write_timeout=self.WRITE_TIMEOUT_SECONDS,
            )
        except (OSError, SerialException) as error:
            error_message = f"Could not open serial port at {baud_rate:,} baud: {error}"
            self._connection_errors[device] = error_message
            logger.error(f"{error_message} ({device})")
            self.serial_io_error.emit(device, error_message)
            return False
        self._serial_connections[device] = connection
        self._start_reader(device, connection)
        self._connection_errors.pop(device, None)
        logger.info(f"Serial port opened at {baud_rate} baud: {device}")
        self.serial_connection_changed.emit(device, True, baud_rate)
        return True

    def close_connection(self, device: str) -> bool:
        """Close and forget a serial connection, returning whether one existed."""
        connection = self._serial_connections.pop(device, None)
        if connection is None:
            return False
        baud_rate = int(connection.baudrate)
        reader = self._serial_readers.pop(device, None)
        if reader is not None:
            reader.requestInterruption()
            try:
                connection.cancel_read()
            except (AttributeError, OSError, SerialException):
                pass
        try:
            connection.close()
        except (OSError, SerialException) as error:
            logger.warning(f"Could not close serial port {device}: {error}")
        else:
            logger.info(f"Serial port closed: {device}")
        if reader is not None:
            if not reader.wait(self.READER_STOP_TIMEOUT_MS):
                logger.warning(f"Serial reader did not stop promptly: {device}")
            reader.deleteLater()
        self.serial_connection_changed.emit(device, False, baud_rate)
        return True

    def close_all_connections(self) -> bool:
        """Close every stored serial connection and clear connection errors."""
        had_connections = bool(self._serial_connections)
        for device in list(self._serial_connections):
            self.close_connection(device)
        self._connection_errors.clear()
        return had_connections

    def broadcast_write(
        self,
        data: bytes,
        *,
        devices: list[str] | None = None,
    ) -> list[str]:
        """Write bytes to requested open connections and return successful devices."""
        if not isinstance(data, bytes) or not data:
            raise ValueError("Serial data must be a non-empty bytes object.")
        target_devices = (
            self.connected_devices
            if devices is None
            else list(dict.fromkeys(devices))
        )
        successful_devices: list[str] = []
        for device in target_devices:
            connection = self._serial_connections.get(device)
            if connection is None or not connection.is_open:
                continue
            try:
                written_byte_count = connection.write(data)
                if written_byte_count != len(data):
                    raise SerialTimeoutException(
                        f"Wrote {written_byte_count} of {len(data)} bytes."
                    )
            except (OSError, SerialException) as error:
                error_message = f"Could not write serial data: {error}"
                self._connection_errors[device] = error_message
                logger.error(f"{error_message} ({device})")
                self.serial_io_error.emit(device, error_message)
                self.close_connection(device)
                continue
            successful_devices.append(device)
        return successful_devices

    def synchronize_connections(self, device_baud_rates: dict[str, int]) -> None:
        """Keep open connections aligned with the requested serial devices."""
        requested_devices = set(device_baud_rates)
        for device in list(self._serial_connections):
            if device not in requested_devices or not self.is_device_available(device):
                self.close_connection(device)
        for device, baud_rate in device_baud_rates.items():
            if not self.is_device_available(device):
                self._connection_errors.pop(device, None)
                continue
            self.open_connection(device, baud_rate)

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

    def _start_reader(self, device: str, connection: Serial) -> None:
        reader = _SerialReaderThread(device, connection, self)
        reader.data_received.connect(
            self._handle_data_received,
            Qt.ConnectionType.QueuedConnection,
        )
        reader.failed.connect(
            self._handle_reader_failure,
            Qt.ConnectionType.QueuedConnection,
        )
        self._serial_readers[device] = reader
        reader.start()

    @Slot(str, str)
    def _handle_data_received(self, device: str, message: str) -> None:
        if device in self._serial_connections:
            self.serial_data_received.emit(device, message)

    @Slot(str, str)
    def _handle_reader_failure(self, device: str, error_message: str) -> None:
        if device not in self._serial_connections:
            return
        formatted_error = f"Could not read serial data: {error_message}"
        self._connection_errors[device] = formatted_error
        logger.error(f"{formatted_error} ({device})")
        self.serial_io_error.emit(device, formatted_error)
        self.close_connection(device)

    def _refresh(self) -> None:
        serial_ports = self.get_available_serial_ports()
        previous_ports = {port.device: port for port in self._serial_ports}
        current_ports = {port.device: port for port in serial_ports}
        connected_devices = sorted(current_ports.keys() - previous_ports.keys())
        disconnected_devices = sorted(previous_ports.keys() - current_ports.keys())
        for device in connected_devices:
            formatted_port = self.format_serial_port(current_ports[device])
            logger.info(f"Serial port connected: {formatted_port}")
        for device in disconnected_devices:
            formatted_port = self.format_serial_port(previous_ports[device])
            logger.info(f"Serial port disconnected: {formatted_port}")
        self._serial_ports = serial_ports
        for device in disconnected_devices:
            self.close_connection(device)
            self._connection_errors.pop(device, None)
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
    def format_serial_port(
        port: ListPortInfo,
        *,
        disconnected: bool = False,
    ) -> str:
        """Return a user-facing serial-port label."""
        if port.description and port.description != "n/a":
            formatted_port = f"{port.description} ({port.device})"
        else:
            formatted_port = port.device
        if disconnected:
            return f"[Disconnected] {formatted_port}"
        return formatted_port
