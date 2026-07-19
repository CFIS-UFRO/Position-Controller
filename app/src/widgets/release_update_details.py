"""Release status and release-notes widget."""

from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.utils.releases import ReleaseUpdate, format_release_entries_html
from src.widgets.html_viewer import HtmlViewer

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class ReleaseUpdateDetails(QGroupBox):
    """Display installed/latest versions and published release notes."""

    def __init__(self, release_update: ReleaseUpdate, parent: QWidget | None = None) -> None:
        super().__init__("Release information", parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        status_label = QLabel(
            "A new version is available."
            if release_update.is_update_available
            else "You are using the latest version.",
            self,
        )
        status_label.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #2e7d32;"
            if release_update.is_update_available
            else "font-size: 14px; font-weight: 600;"
        )
        layout.addWidget(status_label)
        version_layout = QGridLayout()
        version_layout.setHorizontalSpacing(12)
        version_layout.setVerticalSpacing(6)
        version_layout.addWidget(QLabel("Current version:", self), 0, 0)
        version_layout.addWidget(QLabel(release_update.current_version, self), 0, 1)
        version_layout.addWidget(QLabel("Latest version:", self), 1, 0)
        version_layout.addWidget(QLabel(release_update.latest_version, self), 1, 1)
        version_layout.setColumnStretch(2, 1)
        layout.addLayout(version_layout)
        release_notes = HtmlViewer(parent=self)
        release_notes.setOpenExternalLinks(False)
        release_notes.setHtml(format_release_entries_html(release_update.releases))
        layout.addWidget(release_notes, 1)
