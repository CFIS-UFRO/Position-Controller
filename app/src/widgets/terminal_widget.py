"""Bounded terminal-style serial communication display."""

from PySide6.QtCore import QDateTime
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QGroupBox,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class TerminalWidget(QGroupBox):
    """Display timestamped serial events in a bounded terminal view."""

    MAXIMUM_LINE_COUNT = 500
    FIXED_HEIGHT = 160

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Terminal", parent)
        self.setFixedHeight(self.FIXED_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self._output = QPlainTextEdit(self)
        self._output.setReadOnly(True)
        self._output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._output.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self._output.document().setMaximumBlockCount(self.MAXIMUM_LINE_COUNT)
        self._output.setStyleSheet(
            "QPlainTextEdit {"
            "background-color: #000000;"
            "color: #00ff00;"
            "selection-background-color: #006600;"
            "selection-color: #ffffff;"
            "}"
        )
        layout.addWidget(self._output)

    def append_message(self, event_type: str, device: str, message: str) -> None:
        """Append one or more timestamped event lines and scroll to the newest."""
        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
        message_lines = message.splitlines() or [""]
        for message_line in message_lines:
            self._output.appendPlainText(
                f"[{timestamp}] [{event_type}] [{device}] {message_line}"
            )
        vertical_scroll_bar = self._output.verticalScrollBar()
        vertical_scroll_bar.setValue(vertical_scroll_bar.maximum())
