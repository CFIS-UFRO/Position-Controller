"""Reusable centered close button for dialogs."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QWidget

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class CloseButtonWidget(QWidget):
    """Centered button that accepts its containing dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        self._close_button = QPushButton("Close", self)
        self._close_button.setDefault(True)
        self._close_button.clicked.connect(self._close_window)
        layout.addWidget(self._close_button, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        QTimer.singleShot(0, self._close_button.setFocus)

    def _close_window(self) -> None:
        window = self.window()
        if isinstance(window, QDialog):
            window.accept()
