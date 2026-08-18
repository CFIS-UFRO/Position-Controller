"""Reusable theme-aware help button."""

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

from src.utils.colors import is_dark_mode
from src.utils.paths import get_help_icon_file_path
from src.windows.help_window import HelpWindow

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class HelpButton(QPushButton):
    """Open a specific help manual from a compact icon button."""

    BUTTON_SIZE = 20
    ICON_SIZE = 14

    def __init__(self, manual_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manual_id = manual_id
        self._help_window: HelpWindow | None = None
        self.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            "HelpButton {"
            " background: transparent;"
            " border: none;"
            "}"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Help: {self._manual_id}")
        self.setAccessibleName(f"Help: {self._manual_id}")
        self._configure_icon()
        self.clicked.connect(self._open_help_window)

    def changeEvent(self, event: QEvent) -> None:
        """Refresh the icon when the application palette changes."""
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        ):
            self._configure_icon()
        super().changeEvent(event)

    def _configure_icon(self) -> None:
        icon_file_path = get_help_icon_file_path(is_dark_mode())
        if icon_file_path.exists():
            self.setIcon(QIcon(str(icon_file_path)))

    def _open_help_window(self) -> None:
        if self._help_window is None:
            self._help_window = HelpWindow(self._manual_id, self.window())
        else:
            self._help_window.open_manual(self._manual_id)
        self._help_window.show_window()
