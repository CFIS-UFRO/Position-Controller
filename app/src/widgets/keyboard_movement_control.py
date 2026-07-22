"""Keyboard controls for broadcasting relative G-code movements."""

from PySide6.QtCore import QEvent, QObject, Qt, Slot
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QWidget,
)

from src.utils.gcode_controller import GCodeController, MovementMode
from src.utils.serial_port_monitor import SerialPortMonitor

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class KeyboardMovementControl(QGroupBox):
    """Send configurable relative movements with keyboard keys."""

    MINIMUM_DISTANCE_MM = 0.001
    MAXIMUM_DISTANCE_MM = 100_000.0
    DEFAULT_DISTANCE_MM = 1.0
    MINIMUM_SPEED_MM_S = 0.1
    MAXIMUM_SPEED_MM_S = 1_000.0
    DEFAULT_SPEED_MM_S = 50.0
    _KEY_DIRECTIONS: dict[int, tuple[float, float, float]] = {
        int(Qt.Key.Key_Q): (-1.0, 0.0, 0.0),
        int(Qt.Key.Key_W): (1.0, 0.0, 0.0),
        int(Qt.Key.Key_A): (0.0, -1.0, 0.0),
        int(Qt.Key.Key_S): (0.0, 1.0, 0.0),
        int(Qt.Key.Key_Z): (0.0, 0.0, -1.0),
        int(Qt.Key.Key_X): (0.0, 0.0, 1.0),
    }

    def __init__(
        self,
        gcode_controller: GCodeController,
        serial_port_monitor: SerialPortMonitor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Keyboard Movement", parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._gcode_controller = gcode_controller
        self._serial_port_monitor = serial_port_monitor
        # Keyboard movement form
        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(2, 1)
        layout.addWidget(QLabel("Keyboard control", self), 0, 0)
        layout.addWidget(QLabel(":", self), 0, 1)
        self._activation_selector = QComboBox(self)
        self._activation_selector.addItem("Disabled", False)
        self._activation_selector.addItem("Enabled", True)
        self._activation_selector.currentIndexChanged.connect(
            self._handle_activation_changed
        )
        layout.addWidget(self._activation_selector, 0, 2)
        self._x_distance_selector = self._create_distance_selector()
        self._y_distance_selector = self._create_distance_selector()
        self._z_distance_selector = self._create_distance_selector()
        self._movement_controls: list[QWidget] = []
        for row_index, (mapping, selector) in enumerate(
            (
                ("Q = −X    W = +X", self._x_distance_selector),
                ("A = −Y    S = +Y", self._y_distance_selector),
                ("Z = −Z    X = +Z", self._z_distance_selector),
            ),
            start=1,
        ):
            mapping_label = QLabel(mapping, self)
            mapping_label.setStyleSheet("font-weight: 600;")
            layout.addWidget(mapping_label, row_index, 0)
            layout.addWidget(QLabel(":", self), row_index, 1)
            layout.addWidget(selector, row_index, 2)
            self._movement_controls.extend((mapping_label, selector))
        speed_label = QLabel("Speed", self)
        layout.addWidget(speed_label, 4, 0)
        layout.addWidget(QLabel(":", self), 4, 1)
        self._speed_selector = QDoubleSpinBox(self)
        self._speed_selector.setRange(self.MINIMUM_SPEED_MM_S, self.MAXIMUM_SPEED_MM_S)
        self._speed_selector.setDecimals(3)
        self._speed_selector.setSingleStep(1.0)
        self._speed_selector.setSuffix(" mm/s")
        self._speed_selector.setValue(self.DEFAULT_SPEED_MM_S)
        layout.addWidget(self._speed_selector, 4, 2)
        self._movement_controls.extend((speed_label, self._speed_selector))
        self._update_availability()
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Handle unmodified movement keys while keyboard control is active."""
        if event.type() != QEvent.Type.KeyPress or not isinstance(event, QKeyEvent):
            return super().eventFilter(watched, event)
        direction = self._KEY_DIRECTIONS.get(event.key())
        if direction is None or not self._can_handle_key_event(event):
            return super().eventFilter(watched, event)
        if not event.isAutoRepeat():
            self._move(*direction)
        return True

    def _create_distance_selector(self) -> QDoubleSpinBox:
        selector = QDoubleSpinBox(self)
        selector.setRange(self.MINIMUM_DISTANCE_MM, self.MAXIMUM_DISTANCE_MM)
        selector.setDecimals(3)
        selector.setSingleStep(1.0)
        selector.setSuffix(" mm")
        selector.setValue(self.DEFAULT_DISTANCE_MM)
        return selector

    def _can_handle_key_event(self, event: QKeyEvent) -> bool:
        if event.modifiers() != Qt.KeyboardModifier.NoModifier:
            return False
        if not bool(self._activation_selector.currentData()):
            return False
        if not self._serial_port_monitor.connected_devices:
            return False
        return True

    def _move(self, x_direction: float, y_direction: float, z_direction: float) -> None:
        self._gcode_controller.move(
            MovementMode.RELATIVE,
            x_direction * self._x_distance_selector.value(),
            y_direction * self._y_distance_selector.value(),
            z_direction * self._z_distance_selector.value(),
            self._speed_selector.value(),
            force_mode=True,
        )

    @Slot(int)
    def _handle_activation_changed(self, _index: int) -> None:
        is_active = bool(self._activation_selector.currentData())
        self._set_movement_controls_enabled(
            is_active and bool(self._serial_port_monitor.connected_devices)
        )

    @Slot(str, bool, int)
    def handle_serial_connection_changed(
        self,
        _device: str,
        _connected: bool,
        _baud_rate: int,
    ) -> None:
        """Update availability and disarm control after the last disconnection."""
        self._update_availability()

    def _update_availability(self) -> None:
        has_connection = bool(self._serial_port_monitor.connected_devices)
        if not has_connection:
            self._activation_selector.setCurrentIndex(0)
        self._activation_selector.setEnabled(has_connection)
        self._set_movement_controls_enabled(
            has_connection and bool(self._activation_selector.currentData())
        )

    def _set_movement_controls_enabled(self, enabled: bool) -> None:
        for control in self._movement_controls:
            control.setEnabled(enabled)
