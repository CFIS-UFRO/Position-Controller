"""Bounded terminal-style serial communication display."""

from PySide6.QtCore import QDateTime, Qt, Slot
from PySide6.QtGui import QColor, QFontDatabase, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.utils.logging import qt_log_handler
from src.widgets.help_group_box import HelpGroupBox

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class TerminalWidget(HelpGroupBox):
    """Display timestamped log records in a bounded terminal view."""

    MAXIMUM_LINE_COUNT = 500
    INITIAL_HEIGHT = 250
    MINIMUM_HEIGHT = 96
    DEFAULT_TEXT_COLOR = "#E0E0E0"
    EVENT_TEXT_COLORS = {
        "INFO": "#40C4FF",
        "WARNING": "#FFD740",
        "ERROR": "#FF5252",
        "CRITICAL": "#FF4081",
    }
    SERIAL_MESSAGE_TEXT_COLORS = {
        "[TX] ": "#B2FF59",
        "[RX] ": "#00E676",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Terminal", "terminal", parent)
        self.setMinimumHeight(self.MINIMUM_HEIGHT)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout = QVBoxLayout(self.content_group_box)
        layout.setContentsMargins(8, 8, 8, 8)
        self._output = QPlainTextEdit(self.content_group_box)
        self._output.setReadOnly(True)
        self._output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._output.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self._output.document().setMaximumBlockCount(self.MAXIMUM_LINE_COUNT)
        self._output.setStyleSheet(
            "QPlainTextEdit {"
            "background-color: #000000;"
            f"color: {self.DEFAULT_TEXT_COLOR};"
            "selection-background-color: #006600;"
            "selection-color: #ffffff;"
            "}"
        )
        layout.addWidget(self._output)
        qt_log_handler.emitter.message_logged.connect(
            self.append_message,
            Qt.ConnectionType.QueuedConnection,
        )

    @Slot(float, str, str)
    def append_message(self, created_at: float, level_name: str, message: str) -> None:
        """Append one or more formatted log lines and scroll to the newest."""
        timestamp = QDateTime.fromMSecsSinceEpoch(
            int(created_at * 1_000)
        ).toString("HH:mm:ss")
        message_lines = message.splitlines() or [""]
        normalized_level_name = level_name.upper()
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for message_line in message_lines:
            text_color = self.EVENT_TEXT_COLORS.get(
                normalized_level_name,
                self.DEFAULT_TEXT_COLOR,
            )
            for prefix, serial_text_color in self.SERIAL_MESSAGE_TEXT_COLORS.items():
                if message_line.startswith(prefix):
                    text_color = serial_text_color
                    break
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(text_color))
            if not self._output.document().isEmpty():
                cursor.insertBlock()
            cursor.insertText(
                f"[{timestamp}] [{level_name}] {message_line}",
                text_format,
            )
        vertical_scroll_bar = self._output.verticalScrollBar()
        vertical_scroll_bar.setValue(vertical_scroll_bar.maximum())
