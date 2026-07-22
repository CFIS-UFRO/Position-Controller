"""G-code generation and multi-port command dispatch."""

import math
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QObject, Signal

from src.utils.serial_port_monitor import SerialPortMonitor

# --------------------------------------------------------------------------------------------------
# Movement modes
# --------------------------------------------------------------------------------------------------
class MovementMode(Enum):
    """Supported G-code positioning modes."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"

# --------------------------------------------------------------------------------------------------
# Per-device state
# --------------------------------------------------------------------------------------------------
@dataclass
class _DeviceGCodeState:
    """Optimistic modal G-code state for one serial device."""

    uses_millimeters: bool = False
    movement_mode: MovementMode | None = None

# --------------------------------------------------------------------------------------------------
# Controller
# --------------------------------------------------------------------------------------------------
class GCodeController(QObject):
    """Generate motion G-code and broadcast it through the serial monitor."""

    command_sent = Signal(str, str)

    def __init__(self, serial_port_monitor: SerialPortMonitor) -> None:
        super().__init__(serial_port_monitor)
        self._serial_port_monitor = serial_port_monitor
        self._device_states = {
            device: _DeviceGCodeState()
            for device in self._serial_port_monitor.connected_devices
        }
        self._serial_port_monitor.serial_connection_changed.connect(
            self._handle_serial_connection_changed
        )

    def set_current_position_as_origin(self) -> None:
        """Set the current X, Y, and Z coordinates to zero on every open port."""
        successful_devices = self._write_command("G92 X0 Y0 Z0")
        for device in successful_devices:
            state = self._device_states.get(device)
            if state is not None:
                state.movement_mode = None
        self._emit_command_sent(
            successful_devices,
            "SET CURRENT POSITION AS ORIGIN",
        )

    def home_all_axes(self) -> None:
        """Home every axis on every open serial port."""
        successful_devices = self._write_command("G28")
        for device in successful_devices:
            state = self._device_states.get(device)
            if state is not None:
                state.movement_mode = None
        self._emit_command_sent(successful_devices, "HOME ALL AXES")

    def move(
        self,
        mode: MovementMode,
        x_mm: float,
        y_mm: float,
        z_mm: float,
        speed_mm_s: float,
    ) -> None:
        """Send a millimetre-based linear movement to every open serial port."""
        if not isinstance(mode, MovementMode):
            raise TypeError("Movement mode must be a MovementMode value.")
        coordinates = (x_mm, y_mm, z_mm)
        if any(not math.isfinite(coordinate) for coordinate in coordinates):
            raise ValueError("Movement coordinates must be finite numbers.")
        if not math.isfinite(speed_mm_s) or speed_mm_s <= 0:
            raise ValueError("Movement speed must be a positive finite number.")
        positioning_command = "G90" if mode is MovementMode.ABSOLUTE else "G91"
        feed_rate_mm_min = speed_mm_s * 60
        movement_parameters = (
            f"X{self._format_number(x_mm)} "
            f"Y{self._format_number(y_mm)} "
            f"Z{self._format_number(z_mm)} "
            f"F{self._format_number(feed_rate_mm_min)}"
        )
        target_devices = self._serial_port_monitor.connected_devices
        for device in target_devices:
            self._device_states.setdefault(device, _DeviceGCodeState())
        millimeter_devices = [
            device
            for device in target_devices
            if not self._device_states[device].uses_millimeters
        ]
        configured_millimeter_devices = self._write_command(
            "G21",
            devices=millimeter_devices,
        )
        for device in configured_millimeter_devices:
            state = self._device_states.get(device)
            if state is not None:
                state.uses_millimeters = True
        self._emit_command_sent(
            configured_millimeter_devices,
            "SET UNITS TO MILLIMETERS",
        )
        mode_devices: list[str] = []
        for device in target_devices:
            state = self._device_states.get(device)
            if (
                state is not None
                and state.uses_millimeters
                and state.movement_mode is not mode
                and self._serial_port_monitor.is_device_connected(device)
            ):
                mode_devices.append(device)
        configured_mode_devices = self._write_command(
            positioning_command,
            devices=mode_devices,
        )
        for device in configured_mode_devices:
            state = self._device_states.get(device)
            if state is not None:
                state.movement_mode = mode
        self._emit_command_sent(
            configured_mode_devices,
            f"SET POSITIONING MODE TO {mode.name}",
        )
        movement_devices: list[str] = []
        for device in target_devices:
            state = self._device_states.get(device)
            if (
                state is not None
                and state.uses_millimeters
                and state.movement_mode is mode
                and self._serial_port_monitor.is_device_connected(device)
            ):
                movement_devices.append(device)
        successful_devices = self._write_command(
            f"G1 {movement_parameters}",
            devices=movement_devices,
        )
        self._emit_command_sent(
            successful_devices,
            f"{mode.name} MOVE {movement_parameters}",
        )

    def _handle_serial_connection_changed(
        self,
        device: str,
        connected: bool,
        _baud_rate: int,
    ) -> None:
        if connected:
            self._device_states[device] = _DeviceGCodeState()
        else:
            self._device_states.pop(device, None)

    def _write_command(
        self,
        command: str,
        *,
        devices: list[str] | None = None,
    ) -> list[str]:
        return self._serial_port_monitor.broadcast_write(
            f"{command}\n".encode("ascii"),
            devices=devices,
        )

    def _emit_command_sent(self, devices: list[str], description: str) -> None:
        for device in devices:
            self.command_sent.emit(device, description)

    @staticmethod
    def _format_number(value: float) -> str:
        formatted_value = f"{value:.3f}".rstrip("0").rstrip(".")
        return "0" if formatted_value in {"-0", ""} else formatted_value
