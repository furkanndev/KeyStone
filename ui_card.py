"""
Compact Package Card Widget
High-density layout designed to fit maximum applications without text overlap.
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent


class PackageCard(QFrame):
    """Card representing an installable software package in the compact grid."""

    hovered = pyqtSignal(dict)
    state_changed = pyqtSignal(dict, bool)
    website_opened = pyqtSignal(dict)

    def __init__(self, pkg: dict, is_installed: bool = False, theme: str = "dark"):
        super().__init__()
        self.pkg = pkg
        self.is_installed = is_installed
        self.current_theme = theme
        self.setProperty("class", "pkgCard")
        self.setProperty("checked", "false")
        self.setFixedHeight(74)

        self._init_ui()
        self.update_theme(theme)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(2)

        # Top Row: Checkbox + Badges
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self.checkbox = QCheckBox(self.pkg["name"].replace("&", "&&"))
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._on_toggled)
        top_row.addWidget(self.checkbox, stretch=1)

        # Update card state based on initial check
        if self.checkbox.isChecked():
            self.setProperty("checked", "true")

        # Portable badge (replaces Recommended)
        if self.pkg.get("portable"):
            port_badge = QLabel("Portable")
            port_badge.setProperty("class", "pkgPortableBadge")
            port_badge.setFixedHeight(18)
            top_row.addWidget(port_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.status_badge = QLabel()
        self.status_badge.setFixedHeight(18)
        if self.is_installed:
            self.status_badge.setText("Kurulu")
            self.status_badge.setProperty("class", "pkgInstalledBadge")
        else:
            self.status_badge.setText("Bekliyor")
            self.status_badge.setProperty("class", "pkgTag")
        top_row.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(top_row)

        # Bottom Row: Short description
        desc_container = QHBoxLayout()
        desc_container.setContentsMargins(44, 0, 0, 0)

        self.desc_label = QLabel(self.pkg["short_desc"])
        self.desc_label.setProperty("class", "pkgDesc")
        self.desc_label.setWordWrap(True)
        desc_container.addWidget(self.desc_label)

        main_layout.addLayout(desc_container)
        main_layout.addStretch(1)

    _last_opened_time = 0.0

    def contextMenuEvent(self, event):
        self._open_official_site()
        event.accept()

    def _open_official_site(self):
        import time
        now = time.time()
        if now - PackageCard._last_opened_time < 0.8:
            return
        PackageCard._last_opened_time = now

        url = self.pkg.get("website") or self.pkg.get("url")
        if url:
            import webbrowser
            webbrowser.open(url)
            self.website_opened.emit(self.pkg)

    def _on_toggled(self, checked: bool):
        self.setProperty("checked", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.hovered.emit(self.pkg)
        self.state_changed.emit(self.pkg, checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
            self.hovered.emit(self.pkg)
            event.accept()
            return
        super().mousePressEvent(event)

    def update_theme(self, theme: str = "dark"):
        self.current_theme = theme
        c_cat = "#00F0FF" if theme == "dark" else "#0284C7"
        c_desc = "#00FF66" if theme == "dark" else "#15803D"
        c_meta = "#8C99AA" if theme == "dark" else "#475569"
        c_hint = "#00F0FF" if theme == "dark" else "#0284C7"

        self.setToolTip("")
        self.style().unpolish(self)
        self.style().polish(self)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def set_installed_status(self, is_installed: bool):
        self.is_installed = is_installed
        if is_installed:
            self.status_badge.setText("Kurulu")
            self.status_badge.setProperty("class", "pkgInstalledBadge")
            self.status_badge.setStyleSheet("")
            self.status_badge.style().unpolish(self.status_badge)
            self.status_badge.style().polish(self.status_badge)

    def set_installing_status(self, text: str = "Yukleniyor..."):
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet("")
        self.status_badge.setProperty("class", "pkgStatusInstalling")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def set_finished_status(self, success: bool, msg: str = ""):
        if success:
            display_text = "Indirildi" if "ndirildi" in msg else "Tamamlandi"
            self.status_badge.setText(display_text)
            self.status_badge.setProperty("class", "pkgStatusSuccess")
        else:
            self.status_badge.setText("Hata")
            self.status_badge.setProperty("class", "pkgStatusError")
        self.status_badge.setStyleSheet("")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def is_selected(self) -> bool:
        return self.checkbox.isChecked()

    def set_selected(self, selected: bool):
        self.checkbox.setChecked(selected)

    def enterEvent(self, event: QEvent):
        """When mouse hovers over the card, update Top Intel Panel."""
        self.hovered.emit(self.pkg)
        super().enterEvent(event)
