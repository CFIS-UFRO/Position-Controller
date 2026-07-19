"""Searchable help-manual navigation and content viewer."""

import re

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QGroupBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.utils.help import get_help_manuals
from src.utils.paths import get_help_dir_path
from src.widgets.html_viewer import HtmlViewer, HtmlViewerStyle

# --------------------------------------------------------------------------------------------------
# Item data roles
# --------------------------------------------------------------------------------------------------
MANUAL_ID_ROLE = int(Qt.ItemDataRole.UserRole)
MANUAL_FILE_ROLE = MANUAL_ID_ROLE + 1
MANUAL_SEARCH_TEXT_ROLE = MANUAL_ID_ROLE + 2

# --------------------------------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------------------------------
class HelpManuals(QGroupBox):
    """Search, select, and display indexed HTML help manuals."""

    def __init__(
        self,
        initial_manual_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._manuals = get_help_manuals()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter)
        left_panel = QWidget(splitter)
        left_panel.setMinimumWidth(220)
        left_panel.setMaximumWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        self._search_input = QLineEdit(left_panel)
        self._search_input.setPlaceholderText("Filter manuals...")
        self._search_input.textChanged.connect(self._reset_search_timer)
        self._search_input.returnPressed.connect(self._apply_search_filter)
        left_layout.addWidget(self._search_input)
        self._manual_list = QListWidget(left_panel)
        self._manual_list.currentItemChanged.connect(self._handle_current_manual_changed)
        left_layout.addWidget(self._manual_list)
        splitter.addWidget(left_panel)
        self._search_timer = QTimer(left_panel)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_search_filter)
        help_dir_path = get_help_dir_path()
        self._manual_viewer = HtmlViewer(
            HtmlViewerStyle(include_links=True, include_h1=True, h2_margin="24px 0 8px"),
            splitter,
        )
        self._manual_viewer.setSearchPaths([str(help_dir_path)])
        self._manual_viewer.document().setBaseUrl(QUrl.fromLocalFile(f"{help_dir_path}/"))
        self._manual_viewer.setOpenLinks(False)
        self._manual_viewer.anchorClicked.connect(self._handle_manual_link_clicked)
        splitter.addWidget(self._manual_viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        for manual in self._manuals:
            item = QListWidgetItem(manual["title"], self._manual_list)
            item.setData(MANUAL_ID_ROLE, manual["id"])
            item.setData(MANUAL_FILE_ROLE, manual["file"])
            manual_file_path = help_dir_path / manual["file"]
            try:
                raw_html = manual_file_path.read_text(encoding="utf-8")
            except OSError:
                searchable_text = ""
            else:
                searchable_text = re.sub(r"<[^>]+>", "", raw_html)
                searchable_text = re.sub(r"\s+", " ", searchable_text).strip()
            item.setData(MANUAL_SEARCH_TEXT_ROLE, searchable_text)
        if initial_manual_id is not None:
            self.open_manual(initial_manual_id)
        elif self._manual_list.count() > 0:
            self._manual_list.setCurrentRow(0)

    def open_manual(self, manual_id: str) -> None:
        """Select a help manual by identifier."""
        for index in range(self._manual_list.count()):
            item = self._manual_list.item(index)
            if item is not None and item.data(MANUAL_ID_ROLE) == manual_id:
                self._manual_list.setCurrentItem(item)
                return
        self._manual_list.setCurrentRow(-1)
        self._manual_list.clearSelection()
        self._manual_viewer.clear()

    def get_current_manual_log_entry(self) -> str:
        """Return a human-readable description of the selected manual."""
        current_item = self._manual_list.currentItem()
        if current_item is None:
            return "none"
        return f"{current_item.text()} ({current_item.data(MANUAL_ID_ROLE)})"

    def _reset_search_timer(self) -> None:
        self._search_timer.start(300)

    def _apply_search_filter(self) -> None:
        self._search_timer.stop()
        search_text = self._search_input.text().lower()
        for index in range(self._manual_list.count()):
            item = self._manual_list.item(index)
            if item is None:
                continue
            title_match = search_text in item.text().lower()
            content_match = search_text in str(item.data(MANUAL_SEARCH_TEXT_ROLE) or "").lower()
            item.setHidden(not (title_match or content_match))

    def _handle_current_manual_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            self._manual_viewer.clear()
            return
        self._manual_viewer.setSource(QUrl(str(current.data(MANUAL_FILE_ROLE))))

    def _handle_manual_link_clicked(self, url: QUrl) -> None:
        if url.scheme() in {"http", "https"}:
            QDesktopServices.openUrl(url)
            return
        manual_file = self._get_manual_file_from_url(url)
        if manual_file is None or not self._select_manual_file(manual_file):
            QDesktopServices.openUrl(url)

    def _select_manual_file(self, manual_file: str) -> bool:
        for index in range(self._manual_list.count()):
            item = self._manual_list.item(index)
            if item is not None and item.data(MANUAL_FILE_ROLE) == manual_file:
                self._manual_list.setCurrentItem(item)
                return True
        return False

    def _get_manual_file_from_url(self, url: QUrl) -> str | None:
        source_path = url.toLocalFile() if url.isLocalFile() else url.toString()
        source_path = source_path.split("#", 1)[0].split("?", 1)[0]
        if not source_path:
            return None
        help_dir_path = get_help_dir_path()
        if url.isLocalFile():
            try:
                return str(
                    help_dir_path.joinpath(source_path).resolve().relative_to(help_dir_path.resolve())
                )
            except ValueError:
                return None
        return source_path
