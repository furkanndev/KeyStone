"""
Interactive Windows Tweak Card Widget
Displays a registry/system optimization with status detection and hover info.
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from tweaks_manager import check_tweak
from locales import t, get_tweak_meta


class TweakCard(QFrame):
    """Card representing a Windows registry tweak."""

    hovered = pyqtSignal(dict)
    state_changed = pyqtSignal(dict, bool)

    def __init__(self, tweak: dict, theme: str = "dark"):
        super().__init__()
        self.tweak = tweak
        self.current_theme = theme
        self.is_active = check_tweak(tweak)
        self.setProperty("class", "pkgCard")
        self.setProperty("checked", "false")
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._init_ui()
        if self.is_active:
            self.set_selected(True)
        self.update_theme(theme)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 8, 14, 8)
        main_layout.setSpacing(4)

        # Top Row: Checkbox + Spacer + Badges
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        name, short_desc, _ = get_tweak_meta(self.tweak)
        self.checkbox = QCheckBox(name.replace("&", "&&"))
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._on_toggled)
        top_row.addWidget(self.checkbox, stretch=1)

        # Update card state based on initial check
        if self.checkbox.isChecked():
            self.setProperty("checked", "true")

        # Status Badge
        self.status_badge = QLabel()
        self.status_badge.setFixedHeight(20)
        if self.is_active:
            self.status_badge.setText(t("tweak_status_active"))
            self.status_badge.setProperty("class", "pkgInstalledBadge")
        else:
            self.status_badge.setText(t("tweak_status_inactive"))
            self.status_badge.setProperty("class", "pkgTag")
        top_row.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(top_row)

        # Bottom Row: Short description aligned under title
        desc_container = QHBoxLayout()
        desc_container.setContentsMargins(46, 0, 0, 0)
        desc_container.setSpacing(0)

        self.desc_label = QLabel(short_desc)
        self.desc_label.setProperty("class", "pkgDesc")
        self.desc_label.setWordWrap(True)
        desc_container.addWidget(self.desc_label)

        main_layout.addLayout(desc_container)


    def _on_toggled(self, checked: bool):
        self.setProperty("checked", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.hovered.emit(self.tweak)
        self.state_changed.emit(self.tweak, checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
            self.hovered.emit(self.tweak)
            event.accept()
            return
        super().mousePressEvent(event)

    def update_theme(self, theme: str = "dark"):
        self.current_theme = theme
        c_cat = "#00F0FF" if theme == "dark" else "#0284C7"
        c_desc = "#00FF66" if theme == "dark" else "#15803D"
        c_meta = "#8C99AA" if theme == "dark" else "#475569"

        self.setToolTip("")
        self.style().unpolish(self)
        self.style().polish(self)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def set_applied_status(self, success: bool, msg: str = ""):
        if success:
            self.is_active = True
            self.status_badge.setText(f"[{t('hud_active')}]")
            self.status_badge.setProperty("class", "pkgStatusSuccess")
            self.set_selected(True)
        else:
            self.status_badge.setText(f"[{t('card_status_error')}]")
            self.status_badge.setProperty("class", "pkgStatusError")
        self.status_badge.setStyleSheet("")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_reverted_status(self, success: bool, msg: str = ""):
        if success:
            self.is_active = False
            self.status_badge.setText(f"[{t('hud_inactive')}]")
            self.status_badge.setProperty("class", "pkgStatusWarning")
            self.set_selected(False)
        else:
            self.status_badge.setText(f"[{t('card_status_error')}]")
            self.status_badge.setProperty("class", "pkgStatusError")
        self.status_badge.setStyleSheet("")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.style().unpolish(self)
        self.style().polish(self)

    def refresh_status(self):
        """Re-check registry to reflect active/inactive status and set toggle accordingly."""
        self.is_active = check_tweak(self.tweak)
        self.status_badge.setStyleSheet("")
        if self.is_active:
            self.status_badge.setText(t("tweak_status_active"))
            self.status_badge.setProperty("class", "pkgInstalledBadge")
            self.set_selected(True)
        else:
            self.status_badge.setText(t("tweak_status_inactive"))
            self.status_badge.setProperty("class", "pkgTag")
            self.set_selected(False)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.style().unpolish(self)
        self.style().polish(self)

    def retranslate_ui(self):
        """Retranslate card labels and status badge when language changes."""
        name, short_desc, _ = get_tweak_meta(self.tweak)
        self.checkbox.setText(name.replace("&", "&&"))
        self.desc_label.setText(short_desc)
        if hasattr(self, "status_badge"):
            if self.is_active:
                self.status_badge.setText(t("tweak_status_active"))
            else:
                self.status_badge.setText(t("tweak_status_inactive"))

    def is_selected(self) -> bool:
        return self.checkbox.isChecked()

    def set_selected(self, selected: bool):
        self.checkbox.setChecked(selected)
        self.setProperty("checked", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, event: QEvent):
        """When mouse hovers over the card, update Top Intel Panel."""
        self.hovered.emit(self.tweak)
        super().enterEvent(event)

    def set_dynamic_scale(self, is_large: bool):
        """Dynamically scales font size based on window size."""
        if getattr(self, "_is_scaled_large", None) == is_large:
            return
        self._is_scaled_large = is_large
        if is_large:
            self.checkbox.setStyleSheet("font-size: 14px; font-weight: 600;")
            self.desc_label.setStyleSheet("font-size: 11.5px;")
        else:
            self.checkbox.setStyleSheet("")
            self.desc_label.setStyleSheet("")


