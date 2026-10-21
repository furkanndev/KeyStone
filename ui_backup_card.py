"""
Compact Backup Card Widget
Represents an application or system setting that can be backed up or restored.
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal, QEvent


class BackupCard(QFrame):
    """Card representing a backup/restore item in the grid."""

    hovered = pyqtSignal(dict)
    state_changed = pyqtSignal(dict, bool)

    def __init__(self, item: dict, mode: str = "backup", backup_dir: str = "", theme: str = "dark"):
        super().__init__()
        self.item = item
        self.mode = mode
        self.backup_dir = backup_dir
        self.current_theme = theme
        self.setProperty("class", "pkgCard")
        self.setProperty("checked", "false")
        self.setFixedHeight(80)

        self._init_ui()
        self.update_theme(theme)
        self.update_status(self.mode, self.backup_dir)

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

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 6, 12, 6)
        main_layout.setSpacing(3)

        # Top Row: Checkbox + Spacer + Badges
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.checkbox = QCheckBox(self.item["name"].replace("&", "&&"))
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setChecked(False)
        self.checkbox.toggled.connect(self._on_toggled)
        top_row.addWidget(self.checkbox, stretch=1)

        self.status_badge = QLabel()
        self.status_badge.setFixedHeight(20)
        self.status_badge.setProperty("class", "pkgTag")
        top_row.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(top_row)

        # Bottom Row: Short description
        desc_container = QHBoxLayout()
        desc_container.setContentsMargins(48, 0, 0, 0)

        self.desc_label = QLabel(self.item["short_desc"])
        self.desc_label.setProperty("class", "pkgDesc")
        self.desc_label.setWordWrap(True)
        desc_container.addWidget(self.desc_label)

        main_layout.addLayout(desc_container)
        main_layout.addStretch(1)

    def update_status(self, mode: str, backup_dir: str):
        """Update detection status depending on Backup vs Restore mode."""
        self.mode = mode
        self.backup_dir = backup_dir

        if mode == "backup":
            source_detected = self.item["detect_source"]()
            if source_detected:
                self.status_badge.setText("[Mevcut]")
                self.status_badge.setProperty("class", "pkgInstalledBadge")
            else:
                self.status_badge.setText("[Bulunamadı]")
                self.status_badge.setProperty("class", "pkgTag")
                self.checkbox.setChecked(False)
        else:
            # Restore mode: checks if backup data exists in target directory
            has_backup = self.item["detect_backup"](backup_dir) if backup_dir else False
            if has_backup:
                self.status_badge.setText("[Yedek Var]")
                self.status_badge.setProperty("class", "pkgInstalledBadge")
            else:
                self.status_badge.setText("[Yedek Yok]")
                self.status_badge.setProperty("class", "pkgTag")
                self.checkbox.setChecked(False)

        self.status_badge.setStyleSheet("")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def set_action_status(self, text: str, is_success: bool):
        self.status_badge.setText(f"[{text}]")
        self.status_badge.setStyleSheet("")
        self.status_badge.setProperty("class", "pkgStatusSuccess" if is_success else "pkgStatusError")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def _on_toggled(self, checked: bool):
        self.setProperty("checked", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.hovered.emit(self.item)
        self.state_changed.emit(self.item, checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
            self.hovered.emit(self.item)
            event.accept()
            return
        super().mousePressEvent(event)

    def is_selected(self) -> bool:
        return self.checkbox.isChecked()

    def set_selected(self, selected: bool):
        self.checkbox.setChecked(selected)

    def enterEvent(self, event: QEvent):
        self.hovered.emit(self.item)
        super().enterEvent(event)
