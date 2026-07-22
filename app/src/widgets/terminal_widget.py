"""Bounded terminal-style serial communication display."""

from PySide6.QtCore import QDateTime
from PySide6.QtGui import QColor, QFontDatabase, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QGroupBox,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.utils.logging import logger

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class TerminalWidget(QGroupBox):
    """Display timestamped serial events in a bounded terminal view."""

    MAXIMUM_LINE_COUNT = 500
    FIXED_HEIGHT = 160
    DEFAULT_TEXT_COLOR = "#E0E0E0"
    EVENT_TEXT_COLORS = {
        "DEBUG": "#90A4AE",
        "INFO": "#40C4FF",
        "TX": "#B2FF59",
        "RX": "#00E676",
        "SUCCESS": "#64FFDA",
        "WARNING": "#FFD740",
        "WARN": "#FFD740",
        "ERROR": "#FF5252",
        "CRITICAL": "#FF4081",
        "FATAL": "#FF4081",
    }
    EVENT_LOG_LEVELS = {
        "DEBUG": logger.debug,
        "INFO": logger.info,
        "TX": logger.info,
        "RX": logger.info,
        "SUCCESS": logger.info,
        "WARNING": logger.warning,
        "WARN": logger.warning,
        "ERROR": logger.error,
        "CRITICAL": logger.critical,
        "FATAL": logger.critical,
    }

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
            f"color: {self.DEFAULT_TEXT_COLOR};"
            "selection-background-color: #006600;"
            "selection-color: #ffffff;"
            "}"
        )
        layout.addWidget(self._output)

    def append_message(self, event_type: str, device: str, message: str) -> None:
        """Append one or more timestamped event lines and scroll to the newest."""
        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
        message_lines = message.splitlines() or [""]
        normalized_event_type = event_type.upper()
        text_format = QTextCharFormat()
        text_format.setForeground(
            QColor(
                self.EVENT_TEXT_COLORS.get(
                    normalized_event_type,
                    self.DEFAULT_TEXT_COLOR,
                )
            )
        )
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        log_message = self.EVENT_LOG_LEVELS.get(
            normalized_event_type,
            logger.info,
        )
        for message_line in message_lines:
            log_message(f"[{event_type}] [{device}] {message_line}")
            if not self._output.document().isEmpty():
                cursor.insertBlock()
            cursor.insertText(
                f"[{timestamp}] [{event_type}] [{device}] {message_line}",
                text_format,
            )
        vertical_scroll_bar = self._output.verticalScrollBar()
        vertical_scroll_bar.setValue(vertical_scroll_bar.maximum())
