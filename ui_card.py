"""
Compact Package Card Widget
High-density layout designed to fit maximum applications without text overlap.
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox, QSizePolicy
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
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._init_ui()
        if self.is_installed:
            self.set_selected(True)
        self.update_theme(theme)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 8, 14, 8)
        main_layout.setSpacing(4)

        # Top Row: Checkbox + Badges
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.checkbox = QCheckBox(self.pkg["name"].replace("&", "&&"))
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._on_toggled)
        top_row.addWidget(self.checkbox, stretch=1)

        # Update card state based on initial check
        if self.checkbox.isChecked():
            self.setProperty("checked", "true")

        # Portable vs Setup badge
        is_port = bool(self.pkg.get("portable", False))
        self.type_badge = QLabel("Portable" if is_port else "Setup")
        self.type_badge.setProperty("class", "pkgPortableBadge" if is_port else "pkgSetupBadge")
        self.type_badge.setFixedHeight(18)
        self.type_badge.setToolTip("Taşınabilir Sürüm (Kurulumsuz)" if is_port else "Kurulum Sürümü (Sisteme Yüklenir)")
        top_row.addWidget(self.type_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

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

        # Bottom Row: Short description aligned under title
        desc_container = QHBoxLayout()
        desc_container.setContentsMargins(46, 0, 0, 0)
        desc_container.setSpacing(0)

        self.desc_label = QLabel(self.pkg["short_desc"])
        self.desc_label.setProperty("class", "pkgDesc")
        self.desc_label.setWordWrap(True)
        desc_container.addWidget(self.desc_label)

        main_layout.addLayout(desc_container)


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
        if hasattr(self, "type_badge"):
            self.type_badge.style().unpolish(self.type_badge)
            self.type_badge.style().polish(self.type_badge)

    def set_installed_status(self, is_installed: bool):
        self.is_installed = is_installed
        if is_installed:
            self.status_badge.setText("Kurulu")
            self.status_badge.setProperty("class", "pkgInstalledBadge")
            self.status_badge.setStyleSheet("")
            self.status_badge.style().unpolish(self.status_badge)
            self.status_badge.style().polish(self.status_badge)
            self.set_selected(True)

    def set_installing_status(self, text: str = "Yukleniyor..."):
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet("")
        self.status_badge.setProperty("class", "pkgStatusInstalling")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def set_finished_status(self, success: bool, msg: str = ""):
        if success:
            display_text = "İndirildi" if "ndirildi" in msg else "Tamamlandı"
            self.status_badge.setText(display_text)
            self.status_badge.setProperty("class", "pkgStatusSuccess")
            self.set_selected(False)
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
        self.setProperty("checked", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, event: QEvent):
        """When mouse hovers over the card, update Top Intel Panel."""
        self.hovered.emit(self.pkg)
        super().enterEvent(event)

    def set_dynamic_scale(self, is_large: bool):
        """Dynamically scales font size and spacing based on window size without breaking stylesheet."""
        if getattr(self, "_is_scaled_large", None) == is_large:
            return
        self._is_scaled_large = is_large
        font = self.checkbox.font()
        font.setPointSize(11 if is_large else 10)
        self.checkbox.setFont(font)
        if is_large:
            self.desc_label.setStyleSheet("font-size: 11.5px;")
        else:
            self.desc_label.setStyleSheet("")

