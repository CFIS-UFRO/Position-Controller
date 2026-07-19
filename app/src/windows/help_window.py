"""Application help window."""

import sys

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from src.utils.logging import logger
from src.widgets.close_button_widget import CloseButtonWidget
from src.widgets.help_manuals import HelpManuals

# --------------------------------------------------------------------------------------------------
# Dialog
# --------------------------------------------------------------------------------------------------
class HelpWindow(QDialog):
    """Display the indexed application help manuals."""

    def __init__(
        self,
        initial_manual_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.resize(800, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self._help_manuals = HelpManuals(initial_manual_id, self)
        layout.addWidget(self._help_manuals, 1)
        layout.addWidget(CloseButtonWidget(self))

    def open_manual(self, manual_id: str) -> None:
        """Open a help manual by identifier."""
        self._help_manuals.open_manual(manual_id)

    def show_window(self) -> None:
        """Show, raise, and activate the help window."""
        logger.info(
            f"Opening help window with entry: {self._help_manuals.get_current_manual_log_entry()}"
        )
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        if sys.platform != "darwin":
            self.activateWindow()
