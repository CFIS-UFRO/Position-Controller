"""Theme-aware HTML viewer used for release notes."""

from dataclasses import dataclass

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QTextBrowser, QWidget

# --------------------------------------------------------------------------------------------------
# Style
# --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class HtmlViewerStyle:
    """HTML viewer style settings."""

    include_links: bool = False
    include_h1: bool = False
    h2_margin: str = "0 0 8px"

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class HtmlViewer(QTextBrowser):
    """Text browser with application theme-aware document styling."""

    def __init__(
        self,
        style: HtmlViewerStyle | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._viewer_style = style or HtmlViewerStyle()
        self.apply_theme()

    def apply_theme(self) -> None:
        """Apply colors based on the current Qt palette."""
        colors = self._get_theme_colors()
        font_family = QApplication.font().family()
        self.setStyleSheet(
            f"QTextBrowser, QTextBrowser viewport {{"
            f"background-color: {colors['background']}; color: {colors['text']};"
            "}"
        )
        self.document().setDefaultStyleSheet(
            f"""
            html, body {{
                background-color: {colors["background"]};
                color: {colors["text"]};
                font-family: "{font_family}";
                margin: 20px;
                line-height: 1.5;
            }}
            h1, h2, h3 {{ color: {colors["heading"]}; }}
            {self._get_h1_style_sheet()}
            h2 {{ font-size: 18px; margin: {self._viewer_style.h2_margin}; }}
            p, li {{ font-size: 14px; }}
            {self._get_link_style_sheet(colors)}
            code {{
                background-color: {colors["code_background"]};
                color: {colors["code_text"]};
                padding: 2px 4px;
            }}
            """
        )

    def _get_theme_colors(self) -> dict[str, str]:
        window_color = self.palette().color(QPalette.ColorRole.Window)
        if window_color.lightness() < 128:
            return {
                "background": "#242629",
                "text": "#f1f3f5",
                "heading": "#ffffff",
                "link": "#8ab4f8",
                "code_background": "#34373b",
                "code_text": "#f1f3f5",
            }
        return {
            "background": "#e6e8eb",
            "text": "#222222",
            "heading": "#111111",
            "link": "#1f5fbf",
            "code_background": "#d8dde3",
            "code_text": "#222222",
        }

    def _get_h1_style_sheet(self) -> str:
        if not self._viewer_style.include_h1:
            return ""
        return "h1 { font-size: 24px; margin: 0 0 16px; }"

    def _get_link_style_sheet(self, colors: dict[str, str]) -> str:
        if not self._viewer_style.include_links:
            return ""
        return f"a {{ color: {colors['link']}; }}"
