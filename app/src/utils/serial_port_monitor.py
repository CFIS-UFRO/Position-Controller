"""Serial-port monitoring helpers."""

from PySide6.QtCore import QObject, QTimer
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo

from src.utils.logging import logger

# --------------------------------------------------------------------------------------------------
# Port monitoring
# --------------------------------------------------------------------------------------------------
class SerialPortMonitor(QObject):
    """Track available serial ports and log connection changes."""

    SCAN_INTERVAL_MS = 5_000

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._serial_ports: list[ListPortInfo] = []
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
        for device in sorted(current_ports.keys() - previous_ports.keys()):
            logger.info(f"Serial port connected: {self._format_serial_port(current_ports[device])}")
        for device in sorted(previous_ports.keys() - current_ports.keys()):
            logger.info(f"Serial port disconnected: {self._format_serial_port(previous_ports[device])}")
        self._serial_ports = serial_ports

    @staticmethod
    def get_available_serial_ports() -> list[ListPortInfo]:
        """Return all available serial ports with their discovered metadata."""
        return sorted(list_ports.comports())

    @staticmethod
    def _format_serial_port(port: ListPortInfo) -> str:
        if port.description and port.description != "n/a":
            return f"{port.description} ({port.device})"
        return port.device
