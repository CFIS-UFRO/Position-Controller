"""Reusable badge label widget."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget


# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class BadgeWidget(QLabel):
    """Display centered text on a rounded, colored background."""

    COLORS = {
        "gray": "#6f7378",
        "green": "#1f8f4d",
        "orange": "#c46a1a",
        "red": "#b43a35",
    }

    def __init__(
        self,
        text: str,
        color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(24)
        self.set_color(color)

    def set_color(self, color: str) -> None:
        """Set the badge background to a supported named color."""
        if color not in self.COLORS:
            supported_colors = ", ".join(sorted(self.COLORS))
            raise ValueError(
                f"Unsupported badge color '{color}'. Supported colors: {supported_colors}"
            )
        self.setStyleSheet(
            f"""
            background-color: {self.COLORS[color]};
            border-radius: 12px;
            color: white;
            font-size: 12px;
            font-weight: 600;
            padding: 0 12px;
            """
        )
