"""
Keystone Profile Card and Dialog Widgets
Provides interactive profile cards, detailed item inspectors, and profile creation dialogs.
"""

from typing import Dict, Any, List
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QDialog, QTabWidget, QWidget, QScrollArea, QLineEdit,
    QTextEdit, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from profile_manager import ProfileManager, APP_MAP, TWEAK_MAP, BACKUP_MAP


# =============================================================================
# PROFILE CARD WIDGET
# =============================================================================

class ProfileCard(QFrame):
    """Visual card displaying a setup profile with quick action buttons."""

    apply_requested = pyqtSignal(dict)
    inspect_requested = pyqtSignal(dict)
    update_requested = pyqtSignal(dict)
    export_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    hovered = pyqtSignal(dict)

    def __init__(self, profile: Dict[str, Any], is_active: bool = False):
        super().__init__()
        self.profile = profile
        self.is_active = is_active

        self.setProperty("class", "pkgCard")
        self.setProperty("checked", "true" if is_active else "false")
        self.setMinimumHeight(155)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(6)

        # 1. Header: Name + Badges
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.name_label = QLabel(self.profile["name"])
        self.name_label.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 14px; font-weight: 700; color: #FFFFFF;")
        top_row.addWidget(self.name_label)

        badge_text = self.profile.get("badge", "ÖZEL PROFİL" if not self.profile.get("is_builtin") else "FABRİKA")
        self.badge_lbl = QLabel(f"[{badge_text}]")
        self.badge_lbl.setFixedHeight(22)
        self.badge_lbl.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; "
            "padding: 2px 8px; background-color: #0B2533; color: #00F0FF; border: 1px solid #00F0FF;"
            if self.profile.get("is_builtin") else
            "font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; "
            "padding: 2px 8px; background-color: #2D1432; color: #FF70A6; border: 1px solid #FF70A6;"
        )
        top_row.addWidget(self.badge_lbl)

        self.active_badge = QLabel("[AKTİF]")
        self.active_badge.setFixedHeight(22)
        self.active_badge.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 10px; font-weight: bold; "
            "padding: 2px 8px; background-color: #032410; color: #00FF66; border: 1px solid #00FF66;"
        )
        self.active_badge.setVisible(self.is_active)
        top_row.addWidget(self.active_badge)

        top_row.addStretch()

        created_lbl = QLabel(f"Tarih: {self.profile.get('created_at', '')}")
        created_lbl.setStyleSheet("font-size: 11px; color: #707E94;")
        top_row.addWidget(created_lbl)

        main_layout.addLayout(top_row)

        # 2. Description
        self.desc_lbl = QLabel(self.profile.get("description", ""))
        self.desc_lbl.setStyleSheet("font-size: 11.5px; color: #BAC7D5; line-height: 1.3;")
        self.desc_lbl.setWordWrap(True)
        main_layout.addWidget(self.desc_lbl)

        # 3. Stats & Content Summary Pills
        apps_count = len(self.profile.get("apps", []))
        tweaks_count = len(self.profile.get("tweaks", []))
        backups_count = len(self.profile.get("backups", []))

        # Sample item names
        app_names = [APP_MAP[a]["name"] for a in self.profile.get("apps", []) if a in APP_MAP]
        sample_apps = ", ".join(app_names[:4]) + (f" (+{len(app_names)-4})" if len(app_names) > 4 else "")
        if not sample_apps:
            sample_apps = "Seçili program yok"

        stats_row = QHBoxLayout()
        stats_row.setSpacing(6)

        pill_app = QLabel(f"{apps_count} Program")
        pill_app.setStyleSheet("font-size: 11px; font-weight: 600; padding: 2px 6px; background-color: #171A2E; color: #00F0FF; border: 1px solid #283050;")
        stats_row.addWidget(pill_app)

        pill_tweak = QLabel(f"{tweaks_count} Regedit")
        pill_tweak.setStyleSheet("font-size: 11px; font-weight: 600; padding: 2px 6px; background-color: #171A2E; color: #FFE600; border: 1px solid #283050;")
        stats_row.addWidget(pill_tweak)

        pill_backup = QLabel(f"{backups_count} Yedek")
        pill_backup.setStyleSheet("font-size: 11px; font-weight: 600; padding: 2px 6px; background-color: #171A2E; color: #00FF66; border: 1px solid #283050;")
        stats_row.addWidget(pill_backup)

        summary_preview = QLabel(f"İçerik: {sample_apps}")
        summary_preview.setStyleSheet("font-size: 11px; color: #8C99AA;")
        stats_row.addWidget(summary_preview, stretch=1)

        main_layout.addLayout(stats_row)

        # 4. Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_apply = QPushButton("Bu Profili Uygula")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setStyleSheet(
            "QPushButton { background-color: #00F0FF; color: #000000; font-weight: 700; font-size: 11px; padding: 5px 12px; border: none; } "
            "QPushButton:hover { background-color: #38F8FF; }"
        )
        self.btn_apply.clicked.connect(lambda: self.apply_requested.emit(self.profile))
        btn_row.addWidget(self.btn_apply)

        self.btn_inspect = QPushButton("Detayları İncele")
        self.btn_inspect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inspect.setStyleSheet(
            "QPushButton { background-color: #181A2C; color: #BAC7D5; font-size: 11px; padding: 5px 10px; border: 1px solid #33385C; } "
            "QPushButton:hover { background-color: #23263E; color: #00F0FF; border-color: #00F0FF; }"
        )
        self.btn_inspect.clicked.connect(lambda: self.inspect_requested.emit(self.profile))
        btn_row.addWidget(self.btn_inspect)

        self.btn_update = QPushButton("Seçimlerle Güncelle")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setToolTip("Mevcut program, ayar ve yedekleme seçimlerinizi bu profilin üzerine kaydeder.")
        self.btn_update.setStyleSheet(
            "QPushButton { background-color: #181A2C; color: #BAC7D5; font-size: 11px; padding: 5px 10px; border: 1px solid #33385C; } "
            "QPushButton:hover { background-color: #23263E; color: #FFE600; border-color: #FFE600; }"
        )
        self.btn_update.clicked.connect(lambda: self.update_requested.emit(self.profile))
        btn_row.addWidget(self.btn_update)

        self.btn_export = QPushButton("Dışa Aktar (.json)")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setToolTip("Bu profili flash belleğe veya diske JSON dosyası olarak aktarır.")
        self.btn_export.setStyleSheet(
            "QPushButton { background-color: #181A2C; color: #BAC7D5; font-size: 11px; padding: 5px 10px; border: 1px solid #33385C; } "
            "QPushButton:hover { background-color: #23263E; color: #00FF66; border-color: #00FF66; }"
        )
        self.btn_export.clicked.connect(lambda: self.export_requested.emit(self.profile))
        btn_row.addWidget(self.btn_export)

        if not self.profile.get("is_builtin", False):
            self.btn_delete = QPushButton("Sil")
            self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_delete.setStyleSheet(
                "QPushButton { background-color: #220814; color: #FF4757; font-size: 11px; padding: 5px 10px; border: 1px solid #FF4757; } "
                "QPushButton:hover { background-color: #380C1E; color: #FFA0A0; }"
            )
            self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.profile))
            btn_row.addWidget(self.btn_delete)

        btn_row.addStretch()
        main_layout.addLayout(btn_row)

    def set_active_state(self, is_active: bool):
        self.is_active = is_active
        self.active_badge.setVisible(is_active)
        self.setProperty("checked", "true" if is_active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, event):
        self.hovered.emit(self.profile)
        super().enterEvent(event)


# =============================================================================
# DETAILED PROFILE INSPECTOR DIALOG
# =============================================================================

class ProfileDetailDialog(QDialog):
    """Displays exhaustive checklist of all apps, tweaks, and backups in a profile."""

    def __init__(self, profile: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle(f"Profil Detayı — {profile['name']}")
        self.setMinimumSize(850, 650)
        self.resize(920, 700)
        self.should_apply = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Info Box
        header_box = QFrame()
        header_box.setStyleSheet("background-color: #111322; border: 1px solid #232845; padding: 12px;")
        h_layout = QVBoxLayout(header_box)
        h_layout.setSpacing(4)

        title_row = QHBoxLayout()
        name_lbl = QLabel(self.profile["name"])
        name_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #00F0FF;")
        title_row.addWidget(name_lbl)

        badge_lbl = QLabel(f"[{self.profile.get('badge', 'PROFİL')}]")
        badge_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFE600; background-color: #2D2A10; padding: 2px 8px; border: 1px solid #FFE600;")
        title_row.addWidget(badge_lbl)
        title_row.addStretch()
        h_layout.addLayout(title_row)

        desc_lbl = QLabel(self.profile.get("description", ""))
        desc_lbl.setStyleSheet("color: #BAC7D5; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        h_layout.addWidget(desc_lbl)

        layout.addWidget(header_box)

        # Tabs for Apps, Tweaks, and Backups
        detail_data = ProfileManager.get_profile_detailed_items(self.profile)
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #232845; background: #0E101B; }
            QTabBar::tab { background: #141728; color: #8C99AA; padding: 8px 18px; font-weight: bold; }
            QTabBar::tab:selected { background: #1C2038; color: #00F0FF; border-top: 2px solid #00F0FF; }
        """)

        # Tab 1: Apps
        tab_apps = QWidget()
        apps_layout = QVBoxLayout(tab_apps)
        apps_scroll = QScrollArea()
        apps_scroll.setWidgetResizable(True)
        apps_content = QWidget()
        ac_layout = QVBoxLayout(apps_content)
        ac_layout.setSpacing(6)

        apps_list = detail_data["apps"]
        if apps_list:
            for a in apps_list:
                item_frame = QFrame()
                item_frame.setStyleSheet("background-color: #121526; border: 1px solid #1F243E; padding: 8px;")
                if_layout = QHBoxLayout(item_frame)
                name = QLabel(a['name'])
                name.setStyleSheet("font-weight: bold; color: #FFFFFF; font-size: 13px;")
                cat = QLabel(f"[{a['category'].upper()}]")
                cat.setStyleSheet("color: #00F0FF; font-size: 10px; font-weight: bold;")
                winget = QLabel(f"ID: {a['winget_id']}")
                winget.setStyleSheet("color: #707E94; font-size: 10px;")
                desc = QLabel(a['desc'])
                desc.setStyleSheet("color: #8C99AA; font-size: 11px;")
                desc.setWordWrap(True)

                if_layout.addWidget(name)
                if_layout.addWidget(cat)
                if_layout.addWidget(winget)
                if_layout.addStretch()
                ac_layout.addWidget(item_frame)
        else:
            ac_layout.addWidget(QLabel("Bu profilde seçili program bulunmuyor."))
        ac_layout.addStretch()
        apps_scroll.setWidget(apps_content)
        apps_layout.addWidget(apps_scroll)
        tabs.addTab(tab_apps, f"Programlar ({len(apps_list)})")

        # Tab 2: Tweaks
        tab_tweaks = QWidget()
        tweaks_layout = QVBoxLayout(tab_tweaks)
        tweaks_scroll = QScrollArea()
        tweaks_scroll.setWidgetResizable(True)
        tweaks_content = QWidget()
        tc_layout = QVBoxLayout(tweaks_content)
        tc_layout.setSpacing(6)

        tweaks_list = detail_data["tweaks"]
        if tweaks_list:
            for t in tweaks_list:
                item_frame = QFrame()
                item_frame.setStyleSheet("background-color: #121526; border: 1px solid #1F243E; padding: 8px;")
                if_layout = QVBoxLayout(item_frame)
                name = QLabel(t['name'])
                name.setStyleSheet("font-weight: bold; color: #FFE600; font-size: 13px;")
                desc = QLabel(t['desc'])
                desc.setStyleSheet("color: #8C99AA; font-size: 11px;")
                desc.setWordWrap(True)
                if_layout.addWidget(name)
                if_layout.addWidget(desc)
                tc_layout.addWidget(item_frame)
        else:
            tc_layout.addWidget(QLabel("Bu profilde seçili Windows ayarı bulunmuyor."))
        tc_layout.addStretch()
        tweaks_scroll.setWidget(tweaks_content)
        tweaks_layout.addWidget(tweaks_scroll)
        tabs.addTab(tab_tweaks, f"Windows Regedit Ayarları ({len(tweaks_list)})")

        # Tab 3: Backups
        tab_backups = QWidget()
        backups_layout = QVBoxLayout(tab_backups)
        backups_scroll = QScrollArea()
        backups_scroll.setWidgetResizable(True)
        backups_content = QWidget()
        bc_layout = QVBoxLayout(backups_content)
        bc_layout.setSpacing(6)

        backups_list = detail_data["backups"]
        if backups_list:
            for b in backups_list:
                item_frame = QFrame()
                item_frame.setStyleSheet("background-color: #121526; border: 1px solid #1F243E; padding: 8px;")
                if_layout = QVBoxLayout(item_frame)
                name = QLabel(b['name'])
                name.setStyleSheet("font-weight: bold; color: #00FF66; font-size: 13px;")
                desc = QLabel(b['desc'])
                desc.setStyleSheet("color: #8C99AA; font-size: 11px;")
                desc.setWordWrap(True)
                if_layout.addWidget(name)
                if_layout.addWidget(desc)
                bc_layout.addWidget(item_frame)
        else:
            bc_layout.addWidget(QLabel("Bu profilde seçili yedekleme öğesi bulunmuyor."))
        bc_layout.addStretch()
        backups_scroll.setWidget(backups_content)
        backups_layout.addWidget(backups_scroll)
        tabs.addTab(tab_backups, f"Yedekleme && Geri Yükleme ({len(backups_list)})")

        layout.addWidget(tabs, stretch=1)

        # Bottom Buttons
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        btn_apply = QPushButton("Bu Profili Uygula ve Kapat")
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.setStyleSheet(
            "QPushButton { background-color: #00F0FF; color: #000000; font-weight: bold; padding: 9px 20px; font-size: 13px; border: none; } "
            "QPushButton:hover { background-color: #38F8FF; }"
        )
        btn_apply.clicked.connect(self._on_apply_clicked)
        bottom_row.addWidget(btn_apply)

        bottom_row.addStretch()

        btn_close = QPushButton("Kapat")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            "QPushButton { background-color: #181A2C; color: #BAC7D5; padding: 8px 18px; border: 1px solid #33385C; font-size: 12px; } "
            "QPushButton:hover { background-color: #23263E; color: #FFFFFF; }"
        )
        btn_close.clicked.connect(self.reject)
        bottom_row.addWidget(btn_close)

        layout.addLayout(bottom_row)

    def _on_apply_clicked(self):
        self.should_apply = True
        self.accept()


# =============================================================================
# CREATE NEW PROFILE DIALOG
# =============================================================================

class CreateProfileDialog(QDialog):
    """Modal dialog allowing user to name and describe a new profile from current selections."""

    def __init__(self, app_count: int, tweak_count: int, backup_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mevcut Seçimlerden Yeni Profil Oluştur")
        self.setMinimumSize(480, 360)
        self.app_count = app_count
        self.tweak_count = tweak_count
        self.backup_count = backup_count

        self.profile_name = ""
        self.profile_desc = ""

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("YENİ FORMAT PROFİLİ OLUŞTUR")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00F0FF;")
        layout.addWidget(title)

        info_box = QFrame()
        info_box.setStyleSheet("background-color: #111425; border: 1px solid #202747; padding: 10px;")
        ib_layout = QHBoxLayout(info_box)
        p1 = QLabel(f"{self.app_count} Program")
        p1.setStyleSheet("color: #00F0FF; font-weight: bold;")
        p2 = QLabel(f"{self.tweak_count} Regedit")
        p2.setStyleSheet("color: #FFE600; font-weight: bold;")
        p3 = QLabel(f"{self.backup_count} Yedek")
        p3.setStyleSheet("color: #00FF66; font-weight: bold;")
        ib_layout.addWidget(p1)
        ib_layout.addWidget(p2)
        ib_layout.addWidget(p3)
        ib_layout.addStretch()
        layout.addWidget(info_box)

        lbl_name = QLabel("Profil Adı:")
        lbl_name.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        layout.addWidget(lbl_name)

        self.name_input = QLineEdit("Kişisel Format Profilim")
        self.name_input.setStyleSheet("background-color: #090B14; color: #FFFFFF; border: 1px solid #00F0FF; padding: 8px; font-size: 13px;")
        layout.addWidget(self.name_input)

        lbl_desc = QLabel("Açıklama / Notlar (İsteğe bağlı):")
        lbl_desc.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        layout.addWidget(lbl_desc)

        self.desc_input = QTextEdit("Format öncesi seçtiğim programlar, kayıt defteri ayarları ve yedekleme seçenekleri.")
        self.desc_input.setMaximumHeight(80)
        self.desc_input.setStyleSheet("background-color: #090B14; color: #E2E8F0; border: 1px solid #232845; padding: 6px; font-size: 12px;")
        layout.addWidget(self.desc_input)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_save = QPushButton("Profili Kaydet")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #00F0FF; color: #000000; font-weight: bold; padding: 9px 20px; border: none; } "
            "QPushButton:hover { background-color: #38F8FF; }"
        )
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_save)

        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            "QPushButton { background-color: #181A2C; color: #BAC7D5; padding: 8px 18px; border: 1px solid #33385C; } "
            "QPushButton:hover { background-color: #23263E; color: #FFFFFF; }"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        layout.addLayout(btn_row)

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir profil adı girin!")
            return
        self.profile_name = name
        self.profile_desc = self.desc_input.toPlainText().strip()
        self.accept()
