"""
Keystone Browser-Style Profile Selector & Dialogs
Provides the top-header browser profile menu and quick dialogs for adding,
renaming, deleting, and switching profiles.
"""

from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMenu, QWidget, QFrame, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from locales import t


# =============================================================================
# ADD NEW PROFILE DIALOG (STARTS COMPLETELY FROM SCRATCH)
# =============================================================================

class AddProfileDialog(QDialog):
    """Dialog to create a brand new profile that starts completely from scratch."""

    def __init__(self, existing_names: List[str], parent=None):
        super().__init__(parent)
        self.existing_names = existing_names
        self.selected_name = ""
        self.selected_icon = ""

        self.setWindowTitle(t("dialog_new_profile_title"))
        self.setMinimumSize(400, 220)
        self.resize(420, 240)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel(t("dialog_new_profile_header"))
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        info_box = QFrame()
        info_box.setObjectName("dialogInfoBox")
        ib_layout = QVBoxLayout(info_box)
        ib_layout.setSpacing(2)
        info_lbl = QLabel(t("dialog_new_profile_info1"))
        info_lbl.setObjectName("dialogInfoTitle")
        info_sub = QLabel(t("dialog_new_profile_info2"))
        info_sub.setObjectName("dialogInfoSub")
        info_sub.setWordWrap(True)
        ib_layout.addWidget(info_lbl)
        ib_layout.addWidget(info_sub)
        layout.addWidget(info_box)

        name_lbl = QLabel(t("dialog_profile_name_lbl"))
        name_lbl.setObjectName("dialogFieldLabel")
        layout.addWidget(name_lbl)

        default_name = f"Profil {len(self.existing_names) + 1}"
        self.name_input = QLineEdit(default_name)
        self.name_input.setObjectName("dialogInput")
        self.name_input.setPlaceholderText(t("dialog_profile_placeholder"))
        layout.addWidget(self.name_input)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_create = QPushButton(t("dialog_btn_create_profile"))
        btn_create.setObjectName("dialogPrimaryBtn")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self._on_create)
        btn_row.addWidget(btn_create)

        btn_cancel = QPushButton(t("dialog_btn_cancel"))
        btn_cancel.setObjectName("dialogSecondaryBtn")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        layout.addLayout(btn_row)

    def _on_create(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, t("msg_warning"), t("dialog_name_empty_warning"))
            return
        self.selected_name = name
        self.selected_icon = ""
        self.accept()

class RenameProfileDialog(QDialog):
    """Dialog to rename the current active profile."""

    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.new_name = current_name
        self.setWindowTitle(t("dialog_rename_title"))
        self.setMinimumSize(360, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        lbl = QLabel(t("dialog_rename_lbl"))
        lbl.setObjectName("dialogFieldLabel")
        layout.addWidget(lbl)

        self.input = QLineEdit(current_name)
        self.input.setObjectName("dialogInput")
        layout.addWidget(self.input)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_save = QPushButton(t("dialog_btn_save"))
        btn_save.setObjectName("dialogPrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        btn_cancel = QPushButton(t("dialog_btn_cancel"))
        btn_cancel.setObjectName("dialogSecondaryBtn")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        layout.addLayout(btn_row)

    def _on_save(self):
        val = self.input.text().strip()
        if not val:
            QMessageBox.warning(self, t("msg_warning"), t("dialog_name_empty_warning"))
            return
        self.new_name = val
        self.accept()
