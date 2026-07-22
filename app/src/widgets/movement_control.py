"""Positioning controls for broadcasting G-code movements."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from src.utils.gcode_controller import GCodeController, MovementMode
from src.utils.serial_port_monitor import SerialPortMonitor

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class MovementControl(QGroupBox):
    """Configure and send positioning commands to all open serial ports."""

    MINIMUM_COORDINATE_MM = -100_000.0
    MAXIMUM_COORDINATE_MM = 100_000.0
    MINIMUM_SPEED_MM_S = 0.1
    MAXIMUM_SPEED_MM_S = 1_000.0
    DEFAULT_SPEED_MM_S = 50.0

    def __init__(
        self,
        gcode_controller: GCodeController,
        serial_port_monitor: SerialPortMonitor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Movement Control", parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._gcode_controller = gcode_controller
        self._serial_port_monitor = serial_port_monitor
        # Movement form
        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(2, 1)
        self._set_origin_button = QPushButton("Set Current Position as Origin", self)
        self._set_origin_button.clicked.connect(self._set_current_position_as_origin)
        layout.addWidget(self._set_origin_button, 0, 0, 1, 3)
        layout.addWidget(QLabel("Movement type", self), 1, 0)
        layout.addWidget(QLabel(":", self), 1, 1)
        self._movement_type_selector = QComboBox(self)
        self._movement_type_selector.addItem("Relative", MovementMode.RELATIVE)
        self._movement_type_selector.addItem("Absolute", MovementMode.ABSOLUTE)
        layout.addWidget(self._movement_type_selector, 1, 2)
        self._x_selector = self._create_coordinate_selector()
        self._y_selector = self._create_coordinate_selector()
        self._z_selector = self._create_coordinate_selector()
        for row_index, (axis, selector) in enumerate(
            (
                ("X", self._x_selector),
                ("Y", self._y_selector),
                ("Z", self._z_selector),
            ),
            start=2,
        ):
            layout.addWidget(QLabel(axis, self), row_index, 0)
            layout.addWidget(QLabel(":", self), row_index, 1)
            layout.addWidget(selector, row_index, 2)
        layout.addWidget(QLabel("Speed", self), 5, 0)
        layout.addWidget(QLabel(":", self), 5, 1)
        self._speed_selector = QDoubleSpinBox(self)
        self._speed_selector.setRange(self.MINIMUM_SPEED_MM_S, self.MAXIMUM_SPEED_MM_S)
        self._speed_selector.setDecimals(3)
        self._speed_selector.setSingleStep(1.0)
        self._speed_selector.setSuffix(" mm/s")
        self._speed_selector.setValue(self.DEFAULT_SPEED_MM_S)
        layout.addWidget(self._speed_selector, 5, 2)
        self._send_movement_button = QPushButton("Send Movement", self)
        self._send_movement_button.clicked.connect(self._send_movement)
        layout.addWidget(
            self._send_movement_button,
            6,
            0,
            1,
            3,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        layout.setRowStretch(7, 1)
        # Keep command availability aligned with actual open connections.
        self._serial_port_monitor.serial_connection_changed.connect(
            self._handle_serial_connection_changed
        )
        self._set_command_buttons_enabled(bool(self._serial_port_monitor.connected_devices))

    def _create_coordinate_selector(self) -> QDoubleSpinBox:
        selector = QDoubleSpinBox(self)
        selector.setRange(self.MINIMUM_COORDINATE_MM, self.MAXIMUM_COORDINATE_MM)
        selector.setDecimals(3)
        selector.setSingleStep(1.0)
        selector.setSuffix(" mm")
        selector.setValue(0.0)
        return selector

    def _set_current_position_as_origin(self) -> None:
        self._gcode_controller.set_current_position_as_origin()

    def _send_movement(self) -> None:
        movement_mode = self._movement_type_selector.currentData()
        if not isinstance(movement_mode, MovementMode):
            return
        self._gcode_controller.move(
            movement_mode,
            self._x_selector.value(),
            self._y_selector.value(),
            self._z_selector.value(),
            self._speed_selector.value(),
        )

    def _handle_serial_connection_changed(
        self,
        _device: str,
        _connected: bool,
        _baud_rate: int,
    ) -> None:
        self._set_command_buttons_enabled(bool(self._serial_port_monitor.connected_devices))

    def _set_command_buttons_enabled(self, enabled: bool) -> None:
        self._set_origin_button.setEnabled(enabled)
        self._send_movement_button.setEnabled(enabled)
