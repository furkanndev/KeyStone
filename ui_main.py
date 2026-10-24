"""
Keystone Main Application Window
Refined with:
- Dedicated Windows Registry Tweaks tab (Classic context menu, 260 char path limit, etc.)
- 140+ software packages in modern grid with dynamic typography
- Full selection tools (Select All, Clear, Presets) on all tabs
- Custom vector icons
- Top-positioned dynamic intel panel
"""

import os
import json
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QFrame, QGridLayout, QStackedWidget,
    QMenu, QDialog, QSplitter, QSizePolicy, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap, QKeySequence, QShortcut

from data.packages import PACKAGES, CATEGORIES
from data.tweaks import TWEAKS, TWEAK_CATEGORIES
from backup_manager import BACKUP_ITEMS, BackupWorker
from profile_manager import BrowserProfileManager
from ui_card import PackageCard
from ui_tweak_card import TweakCard
from ui_backup_card import BackupCard
from ui_profile_menu import AddProfileDialog, RenameProfileDialog
from installer import is_admin, restart_as_admin, InstallWorker, InstalledScanner, clean_yaml_manifests
from tweaks_manager import apply_tweak, revert_tweak, restart_explorer, check_tweak
from styles import get_stylesheet, get_theme_accent
from utils import resource_path


class MainWindow(QMainWindow):
    """Main Application Window for Keystone."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KeyStone")
        self.setMinimumSize(1080, 800)
        self.resize(1260, 900)

        # State
        self.current_mode = "apps"  # "apps", "tweaks", "backup"
        self.current_app_category = "all"
        self.current_tweak_category = "all"
        self.backup_mode_operation = "backup"  # "backup" or "restore"
        default_backup = r"D:\Keystone_Yedek" if os.path.exists("D:\\") else os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")), "Documents", "Keystone_Yedek"
        )
        self.backup_dir = default_backup
        self.search_filter = ""
        self.app_cards = {}
        self.tweak_cards = {}
        self.backup_cards = {}
        self.worker = None
        self.worker_mode = "install"  # "install" or "download"
        self.last_download_target_dir = ""
        self.installed_ids = set()
        self._app_grid_cols = 1
        self._tweak_grid_cols = 1
        self._backup_grid_cols = 1

        # Browser-style isolated profiles
        self.profile_mgr = BrowserProfileManager()
        self.current_theme = self.profile_mgr.get_theme()
        self._is_switching_profile = False
        self.is_sidebar_collapsed = False
        self.previous_mode = "apps"

        self._init_ui()
        self._load_active_profile_into_ui()
        self._start_installed_scan()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Header Bar
        main_layout.addWidget(self._build_header())

        # 2. INFO PANEL
        main_layout.addWidget(self._build_inspect_panel())

        # 3. Main content area = left sidebar + stacked pages (splitter)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("mainSplitter")
        self.main_splitter.setHandleWidth(1)

        # Left Sidebar Nav
        self.main_splitter.addWidget(self._build_sidebar())

        # Right stacked content
        right_widget = QWidget()
        right_widget.setObjectName("rightPane")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_apps_page())
        self.stack.addWidget(self._build_tweaks_page())
        self.stack.addWidget(self._build_backup_page())
        self.stack.addWidget(self._build_settings_page())
        right_layout.addWidget(self.stack, stretch=1)

        self.main_splitter.addWidget(right_widget)
        self.main_splitter.setSizes([220, 1040])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.splitterMoved.connect(self._on_splitter_moved)

        self.sidebar_shortcut = QShortcut(QKeySequence("Ctrl+B"), self, activated=self._toggle_sidebar)
        self.select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self, activated=self._handle_select_all_shortcut)

        main_layout.addWidget(self.main_splitter, stretch=1)

        # 4. Collapsible Terminal Console (hidden by default)
        self.terminal_console = QTextEdit()
        self.terminal_console.setObjectName("terminalConsole")
        self.terminal_console.setReadOnly(True)
        self.terminal_console.setMaximumHeight(160)
        self.terminal_console.hide()
        main_layout.addWidget(self.terminal_console)

        # 5. Bottom Action Bar
        main_layout.addWidget(self._build_action_bar())

        # Initial Updates
        self._update_counter()
        if PACKAGES:
            self._update_app_hud(PACKAGES[0])
        self._apply_theme(self.current_theme)
        self._update_sidebar_icons(self.current_theme)
        self._update_responsive_bars()
        self._relayout_all_grids()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("headerContainer")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(14)

        # Custom Pixel Art App Icon (42x42)
        icon_path = resource_path("assets/icon.png")
        if os.path.exists(icon_path):
            icon_lbl = QLabel()
            pix = QPixmap(icon_path).scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            icon_lbl.setPixmap(pix)
            icon_lbl.setObjectName("appLogo")
            layout.addWidget(icon_lbl)

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        title = QLabel("KEYSTONE SETUP v1.0")
        title.setObjectName("titleLabel")
        title_box.addWidget(title)

        subtitle = QLabel("Windows Format Sonrası Gerekli Kütüphaneler, Yazılımcı Araçları ve Kayıt Defteri İnce Ayarları")
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(subtitle)

        layout.addLayout(title_box)
        layout.addStretch()

        # Admin Badge / Elevation Button
        if is_admin():
            admin_badge = QLabel("[YÖNETİCİ: AKTİF]")
            admin_badge.setObjectName("adminBadgeElevated")
            layout.addWidget(admin_badge)
        else:
            self.admin_btn = QPushButton("Yönetici Olarak Çalıştır")
            self.admin_btn.setObjectName("adminBadge")
            self.admin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.admin_btn.setToolTip("DirectX, Visual C++ ve Sistem Regedit ayarları için yönetici haklarıyla başlatın.")
            self.admin_btn.clicked.connect(self._elevate_admin)
            layout.addWidget(self.admin_btn)

        # Browser-Style Profile Switcher in Header
        self.btn_profile_switcher = QPushButton("Profil: Varsayılan ▼")
        self.btn_profile_switcher.setObjectName("profileSwitcherBtn")
        self.btn_profile_switcher.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_profile_switcher.clicked.connect(self._show_browser_profile_menu)
        layout.addWidget(self.btn_profile_switcher)

        # Settings Button (toggles settings view)
        self.btn_settings_header = QPushButton("Ayarlar")
        self.btn_settings_header.setObjectName("headerSettingsBtn")
        self.btn_settings_header.setToolTip("Ayarlar & Tercihler (Ctrl+,)")
        self.btn_settings_header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings_header.clicked.connect(self._toggle_settings)
        layout.addWidget(self.btn_settings_header)

        return header

    def _build_sidebar(self) -> QWidget:
        """Left collapsible sidebar navigation panel with pure primary tabs and vector icons."""
        self.sidebar_container = QWidget()
        self.sidebar_container.setObjectName("sidebarContainer")
        self.sidebar_container.setMinimumWidth(180)
        self.sidebar_container.setMaximumWidth(240)

        container_layout = QHBoxLayout(self.sidebar_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 1. SLIM RAIL (Collapsed mode: 50px)
        self.sidebar_rail = QFrame()
        self.sidebar_rail.setObjectName("sidebarPanel")
        self.sidebar_rail.setFixedWidth(50)
        rail_layout = QVBoxLayout(self.sidebar_rail)
        rail_layout.setContentsMargins(6, 10, 6, 10)
        rail_layout.setSpacing(10)

        self.btn_rail_expand = QPushButton()
        self.btn_rail_expand.setIcon(QIcon(resource_path("assets/icons/chevron_right.svg")))
        self.btn_rail_expand.setIconSize(QSize(16, 16))
        self.btn_rail_expand.setObjectName("sidebarToggleBtn")
        self.btn_rail_expand.setToolTip("Sekmeleri Genişlet (Ctrl+B)")
        self.btn_rail_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rail_expand.clicked.connect(self._toggle_sidebar)
        rail_layout.addWidget(self.btn_rail_expand)

        self.btn_rail_apps = QPushButton()
        self.btn_rail_apps.setIcon(QIcon(resource_path("assets/icons/apps.svg")))
        self.btn_rail_apps.setIconSize(QSize(20, 20))
        self.btn_rail_apps.setProperty("class", "sidebarRailBtn")
        self.btn_rail_apps.setProperty("selected", "true")
        self.btn_rail_apps.setToolTip("Yazılım & Programlar")
        self.btn_rail_apps.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rail_apps.clicked.connect(lambda: self._switch_main_mode("apps"))
        rail_layout.addWidget(self.btn_rail_apps)

        self.btn_rail_tweaks = QPushButton()
        self.btn_rail_tweaks.setIcon(QIcon(resource_path("assets/icons/tweaks.svg")))
        self.btn_rail_tweaks.setIconSize(QSize(20, 20))
        self.btn_rail_tweaks.setProperty("class", "sidebarRailBtn")
        self.btn_rail_tweaks.setProperty("selected", "false")
        self.btn_rail_tweaks.setToolTip("Regedit / İnce Ayarlar")
        self.btn_rail_tweaks.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rail_tweaks.clicked.connect(lambda: self._switch_main_mode("tweaks"))
        rail_layout.addWidget(self.btn_rail_tweaks)

        self.btn_rail_backup = QPushButton()
        self.btn_rail_backup.setIcon(QIcon(resource_path("assets/icons/backup.svg")))
        self.btn_rail_backup.setIconSize(QSize(20, 20))
        self.btn_rail_backup.setProperty("class", "sidebarRailBtn")
        self.btn_rail_backup.setProperty("selected", "false")
        self.btn_rail_backup.setToolTip("Yedekleme & Geri Yükle")
        self.btn_rail_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rail_backup.clicked.connect(lambda: self._switch_main_mode("backup"))
        rail_layout.addWidget(self.btn_rail_backup)

        rail_layout.addStretch()
        self.sidebar_rail.hide()
        container_layout.addWidget(self.sidebar_rail)

        # 2. FULL DRAWER (Expanded mode: 220px)
        self.sidebar_drawer = QFrame()
        self.sidebar_drawer.setObjectName("sidebarPanel")
        drawer_layout = QVBoxLayout(self.sidebar_drawer)
        drawer_layout.setContentsMargins(0, 0, 0, 0)
        drawer_layout.setSpacing(6)

        # Top Drawer Action Bar
        drawer_top = QHBoxLayout()
        drawer_top.setContentsMargins(12, 10, 10, 6)
        drawer_top.setSpacing(6)

        drawer_lbl = QLabel("SEKMELER")
        drawer_lbl.setProperty("class", "barSectionLabel")
        drawer_top.addWidget(drawer_lbl)
        drawer_top.addStretch()

        self.btn_drawer_collapse = QPushButton(" Daralt")
        self.btn_drawer_collapse.setIcon(QIcon(resource_path("assets/icons/chevron_left.svg")))
        self.btn_drawer_collapse.setIconSize(QSize(14, 14))
        self.btn_drawer_collapse.setObjectName("sidebarToggleBtn")
        self.btn_drawer_collapse.setToolTip("Sekmeler Panelini Daralt (Ctrl+B)")
        self.btn_drawer_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_drawer_collapse.clicked.connect(self._toggle_sidebar)
        drawer_top.addWidget(self.btn_drawer_collapse)

        drawer_layout.addLayout(drawer_top)

        # Vertical Primary Tab Buttons - Strictly tabs only
        tabs_box = QVBoxLayout()
        tabs_box.setContentsMargins(10, 4, 10, 4)
        tabs_box.setSpacing(6)

        self.tab_btn_apps = QPushButton("  Yazılım & Programlar")
        self.tab_btn_apps.setIcon(QIcon(resource_path("assets/icons/apps.svg")))
        self.tab_btn_apps.setIconSize(QSize(18, 18))
        self.tab_btn_apps.setProperty("class", "sidebarTabBtn")
        self.tab_btn_apps.setProperty("selected", "true")
        self.tab_btn_apps.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_btn_apps.clicked.connect(lambda: self._switch_main_mode("apps"))
        tabs_box.addWidget(self.tab_btn_apps)

        self.tab_btn_tweaks = QPushButton("  Regedit & İnce Ayar")
        self.tab_btn_tweaks.setIcon(QIcon(resource_path("assets/icons/tweaks.svg")))
        self.tab_btn_tweaks.setIconSize(QSize(18, 18))
        self.tab_btn_tweaks.setProperty("class", "sidebarTabBtn")
        self.tab_btn_tweaks.setProperty("selected", "false")
        self.tab_btn_tweaks.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_btn_tweaks.clicked.connect(lambda: self._switch_main_mode("tweaks"))
        tabs_box.addWidget(self.tab_btn_tweaks)

        self.tab_btn_backup = QPushButton("  Yedekleme & Geri Yükle")
        self.tab_btn_backup.setIcon(QIcon(resource_path("assets/icons/backup.svg")))
        self.tab_btn_backup.setIconSize(QSize(18, 18))
        self.tab_btn_backup.setProperty("class", "sidebarTabBtn")
        self.tab_btn_backup.setProperty("selected", "false")
        self.tab_btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_btn_backup.clicked.connect(lambda: self._switch_main_mode("backup"))
        tabs_box.addWidget(self.tab_btn_backup)

        drawer_layout.addLayout(tabs_box)
        drawer_layout.addStretch(1)

        container_layout.addWidget(self.sidebar_drawer)
        return self.sidebar_container

    def _build_inspect_panel(self) -> QWidget:
        """TOP INTEL PANEL: Displays item details at the very top."""
        self.inspect_panel = QFrame()
        self.inspect_panel.setObjectName("inspectPanel")
        layout = QVBoxLayout(self.inspect_panel)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.inspect_badge = QLabel("BİLGİ PANELİ")
        self.inspect_badge.setObjectName("inspectBadge")
        top_row.addWidget(self.inspect_badge)

        self.inspect_title = QLabel("DirectX End-User Runtimes")
        self.inspect_title.setObjectName("inspectTitle")
        top_row.addWidget(self.inspect_title)

        self.inspect_cat_lbl = QLabel("[SİSTEM & RUNTIME]")
        self.inspect_cat_lbl.setObjectName("inspectCatLbl")
        top_row.addWidget(self.inspect_cat_lbl)

        top_row.addStretch()

        self.inspect_source_lbl = QLabel("Paket ID: Microsoft.DirectX")
        self.inspect_source_lbl.setObjectName("inspectMeta")
        top_row.addWidget(self.inspect_source_lbl)

        # Action Hint instead of separate button
        self.inspect_hint_lbl = QLabel("[Sağ Tık: Resmi Site]")
        self.inspect_hint_lbl.setObjectName("inspectHintLbl")
        top_row.addWidget(self.inspect_hint_lbl)

        layout.addLayout(top_row)

        self.inspect_desc = QLabel(
            "Windows formatı sonrası oyunların 'd3dx9_xx.dll bulunamadı' gibi hatalar vermemesi için şarttır. Eski ve modern DirectX bileşenlerini eksiksiz sisteme yükler."
        )
        self.inspect_desc.setObjectName("inspectDesc")
        self.inspect_desc.setWordWrap(True)
        layout.addWidget(self.inspect_desc)

        return self.inspect_panel

    # =========================================================================
    # TAB 1: SOFTWARE PACKAGES PAGE
    # =========================================================================

    def _build_apps_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Preset bar (Redesigned Modern Selector)
        preset_bar = QFrame()
        preset_bar.setObjectName("presetBar")
        self.preset_bar_apps = preset_bar
        p_layout = QHBoxLayout(preset_bar)
        p_layout.setContentsMargins(14, 8, 14, 8)
        p_layout.setSpacing(8)

        lbl = QLabel("Hazır Paket:")
        lbl.setProperty("class", "barSectionLabel")
        p_layout.addWidget(lbl)

        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("presetCombo")
        self.preset_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preset_combo.addItem("Hazır Paket Seçin...", "")
        self.preset_combo.addItem("Temel Runtime Paketi (DirectX, VC++, .NET, 7-Zip)", "essential")
        self.preset_combo.addItem("Yazılımcı (Dev) Paketi (VS Code, Git, Node, Python, Docker)", "dev")
        self.preset_combo.addItem("Veritabanı & Sunucu Paketi (DBeaver, PGAdmin, Redis)", "database")
        self.preset_combo.addItem("Oyuncu Paketi (Steam, Epic, Discord, OBS)", "gamer")
        self.preset_combo.addItem("Yapay Zeka (AI) Paketi (ChatGPT, Claude, Ollama, LM Studio)", "ai")
        self.preset_combo.addItem("Donanım & Test Paketi (CPU-Z, GPU-Z, HWMonitor)", "hardware")
        self.preset_combo.currentIndexChanged.connect(self._on_preset_combo_changed)
        p_layout.addWidget(self.preset_combo)

        self.btn_apply_preset = QPushButton("Paketi Uygula")
        self.btn_apply_preset.setObjectName("presetApplyBtn")
        self.btn_apply_preset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply_preset.setToolTip("Seçili hazır paketteki uygulamaları listeye seçer")
        self.btn_apply_preset.clicked.connect(self._apply_current_preset_combo)
        p_layout.addWidget(self.btn_apply_preset)

        p_layout.addSpacing(6)

        self.btn_toggle_select_apps = QPushButton("Tümünü Seç")
        self.btn_toggle_select_apps.setProperty("class", "presetBtn")
        self.btn_toggle_select_apps.setObjectName("btnToggleSelectAll")
        self.btn_toggle_select_apps.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_select_apps.clicked.connect(self._toggle_select_apps)
        p_layout.addWidget(self.btn_toggle_select_apps)

        self.preset_buttons = {}

        p_layout.addStretch()

        self.app_search_box = QLineEdit()
        self.app_search_box.setObjectName("searchBox")
        self.app_search_box.setPlaceholderText("Program ara (örn: git, steam, docker)...")
        self.app_search_box.setFixedWidth(240)
        self.app_search_box.textChanged.connect(self._on_app_search_changed)
        p_layout.addWidget(self.app_search_box)

        layout.addWidget(preset_bar)

        # Category Bar
        cat_bar = QFrame()
        cat_bar.setObjectName("categoryBar")
        self.cat_bar_apps = cat_bar
        c_layout = QHBoxLayout(cat_bar)
        c_layout.setContentsMargins(14, 5, 14, 5)
        c_layout.setSpacing(6)

        lbl_cat = QLabel("Kategori:")
        lbl_cat.setProperty("class", "barSectionLabel")
        c_layout.addWidget(lbl_cat)

        self.app_category_buttons = {}
        for cat in CATEGORIES:
            btn = QPushButton(cat["name"].replace("&", "&&"))
            btn.setProperty("class", "categoryTab")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setProperty("selected", "true" if cat["id"] == "all" else "false")
            btn.clicked.connect(lambda _, c=cat["id"]: self._switch_app_category(c))
            c_layout.addWidget(btn, stretch=1)
            self.app_category_buttons[cat["id"]] = btn

        layout.addWidget(cat_bar)

        # Scroll area with 3-Column Grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")

        self.app_grid = QGridLayout(scroll_content)
        self.app_grid.setContentsMargins(10, 8, 10, 10)
        self.app_grid.setHorizontalSpacing(8)
        self.app_grid.setVerticalSpacing(7)
        self.app_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._app_grid_cols = 1

        for idx, pkg in enumerate(PACKAGES):
            card = PackageCard(pkg, theme=self.current_theme)
            card.hovered.connect(self._on_card_hovered)
            card.state_changed.connect(self._on_card_toggled)
            card.website_opened.connect(self._on_pkg_website_opened)
            self.app_cards[pkg["id"]] = card
            self.app_grid.addWidget(card, idx, 0)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, stretch=1)
        return page

    # =========================================================================
    # TAB 2: WINDOWS REGISTRY TWEAKS PAGE
    # =========================================================================

    def _build_tweaks_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tweak Presets Bar
        preset_bar = QFrame()
        preset_bar.setObjectName("presetBar")
        self.preset_bar_tweaks = preset_bar
        p_layout = QHBoxLayout(preset_bar)
        p_layout.setContentsMargins(16, 6, 16, 6)
        p_layout.setSpacing(6)

        lbl = QLabel("Seçim:")
        lbl.setProperty("class", "barSectionLabel")
        p_layout.addWidget(lbl)

        self.btn_rec_tweaks = QPushButton("Önerilen Ayarları Seç")
        self.btn_rec_tweaks.setProperty("class", "presetBtn")
        self.btn_rec_tweaks.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rec_tweaks.clicked.connect(self._select_recommended_tweaks)
        p_layout.addWidget(self.btn_rec_tweaks)

        self.btn_active_tweaks = QPushButton("Kurulu / Aktif Olanları Seç")
        self.btn_active_tweaks.setProperty("class", "presetBtn")
        self.btn_active_tweaks.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_active_tweaks.setToolTip("Sisteminizde şu anda aktif olan ince ayarları seçer veya kaldırır.")
        self.btn_active_tweaks.clicked.connect(self._select_active_tweaks)
        p_layout.addWidget(self.btn_active_tweaks)

        self.btn_toggle_select_tweaks = QPushButton("Tümünü Seç")
        self.btn_toggle_select_tweaks.setProperty("class", "presetBtn")
        self.btn_toggle_select_tweaks.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_select_tweaks.clicked.connect(self._toggle_select_tweaks)
        p_layout.addWidget(self.btn_toggle_select_tweaks)

        btn_restart_exp = QPushButton("Dosya Gezginini Yeniden Başlat")
        btn_restart_exp.setProperty("class", "presetBtn")
        btn_restart_exp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restart_exp.setToolTip("Sağ tık ve görünüm ayarlarının anında uygulanması için Explorer'ı yeniden başlatır.")
        btn_restart_exp.clicked.connect(self._restart_explorer_action)
        p_layout.addWidget(btn_restart_exp)

        p_layout.addStretch()

        self.tweak_search_box = QLineEdit()
        self.tweak_search_box.setObjectName("searchBox")
        self.tweak_search_box.setPlaceholderText("Ayar ara (sağ tık, 260 karakter, uac)...")
        self.tweak_search_box.setFixedWidth(260)
        self.tweak_search_box.textChanged.connect(self._on_tweak_search_changed)
        p_layout.addWidget(self.tweak_search_box)

        layout.addWidget(preset_bar)

        # Scroll area with 2-Column Grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")

        self.tweaks_grid = QGridLayout(scroll_content)
        self.tweaks_grid.setContentsMargins(14, 10, 14, 10)
        self.tweaks_grid.setHorizontalSpacing(10)
        self.tweaks_grid.setVerticalSpacing(8)
        self.tweaks_grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._tweak_grid_cols = 1

        for idx, tweak in enumerate(TWEAKS):
            card = TweakCard(tweak, theme=self.current_theme)
            card.hovered.connect(self._on_tweak_hovered)
            card.state_changed.connect(self._on_tweak_toggled)
            self.tweak_cards[tweak["id"]] = card
            self.tweaks_grid.addWidget(card, idx, 0)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, stretch=1)
        return page

    # =========================================================================
    # TAB 3: BACKUP & RESTORE PAGE
    # =========================================================================

    def _build_backup_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Minimal Single Control Bar
        control_bar = QFrame()
        control_bar.setObjectName("presetBar")
        self.control_bar_backup = control_bar
        cb_layout = QHBoxLayout(control_bar)
        cb_layout.setContentsMargins(16, 7, 16, 7)
        cb_layout.setSpacing(8)

        # Mode Selector (Backup vs Restore)
        self.btn_op_backup = QPushButton("Format Öncesi (Yedek Al)")
        self.btn_op_backup.setProperty("class", "categoryTab")
        self.btn_op_backup.setProperty("selected", "true")
        self.btn_op_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_op_backup.clicked.connect(lambda: self._set_backup_operation("backup"))
        cb_layout.addWidget(self.btn_op_backup)

        self.btn_op_restore = QPushButton("Format Sonrası (Geri Yükle)")
        self.btn_op_restore.setProperty("class", "categoryTab")
        self.btn_op_restore.setProperty("selected", "false")
        self.btn_op_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_op_restore.clicked.connect(lambda: self._set_backup_operation("restore"))
        cb_layout.addWidget(self.btn_op_restore)

        folder_lbl = QLabel("Hedef:")
        folder_lbl.setProperty("class", "barSectionLabel")
        cb_layout.addWidget(folder_lbl)

        self.backup_dir_input = QLineEdit(self.backup_dir)
        self.backup_dir_input.setObjectName("searchBox")
        self.backup_dir_input.setToolTip("Yedeklerin saklanacağı veya yükleneceği yerel klasör yolu.")
        self.backup_dir_input.textChanged.connect(self._on_backup_dir_input_changed)
        cb_layout.addWidget(self.backup_dir_input, stretch=1)

        btn_browse = QPushButton("Gözat...")
        btn_browse.setProperty("class", "presetBtn")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.clicked.connect(self._browse_backup_dir)
        cb_layout.addWidget(btn_browse)

        btn_open_folder = QPushButton("Klasörü Aç")
        btn_open_folder.setProperty("class", "presetBtn")
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.clicked.connect(self._open_backup_folder_in_explorer)
        cb_layout.addWidget(btn_open_folder)

        # Smart Toggle & Refresh
        self.btn_toggle_select_backup = QPushButton("Tümünü Seç")
        self.btn_toggle_select_backup.setProperty("class", "presetBtn")
        self.btn_toggle_select_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_select_backup.clicked.connect(self._toggle_select_backup)
        cb_layout.addWidget(self.btn_toggle_select_backup)

        btn_refresh = QPushButton("Yenile")
        btn_refresh.setProperty("class", "presetBtn")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self._refresh_backup_statuses)
        cb_layout.addWidget(btn_refresh)

        layout.addWidget(control_bar)

        # 3. Scroll Area with 2-Column Grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")

        self.backup_grid = QGridLayout(scroll_content)
        self.backup_grid.setContentsMargins(14, 10, 14, 10)
        self.backup_grid.setHorizontalSpacing(10)
        self.backup_grid.setVerticalSpacing(8)
        self.backup_grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._backup_grid_cols = 1

        for idx, item in enumerate(BACKUP_ITEMS):
            card = BackupCard(item, mode=self.backup_mode_operation, backup_dir=self.backup_dir, theme=self.current_theme)
            card.hovered.connect(self._on_backup_hovered)
            card.state_changed.connect(self._on_backup_toggled)
            self.backup_cards[item["id"]] = card
            self.backup_grid.addWidget(card, idx, 0)

        self.backup_grid.setRowStretch(len(BACKUP_ITEMS), 1)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, stretch=1)
        return page



    # =========================================================================
    # ACTION BAR
    # =========================================================================

    def _build_action_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("actionBar")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Hazır [%p%]")
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        row = QHBoxLayout()
        row.setSpacing(12)

        self.counter_lbl = QLabel("Seçilen: 0 Paket")
        self.counter_lbl.setObjectName("selectedCountLabel")
        row.addWidget(self.counter_lbl)

        row.addStretch()

        self.btn_terminal = QPushButton("Konsol Günlüğü")
        self.btn_terminal.setObjectName("terminalToggleBtn")
        self.btn_terminal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_terminal.clicked.connect(self._toggle_terminal)
        row.addWidget(self.btn_terminal)

        self.btn_cancel = QPushButton("İptal Et")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._cancel_installation)
        self.btn_cancel.hide()
        row.addWidget(self.btn_cancel)

        # Download Setups to Folder Button (Active only in Software tab)
        self.btn_download_setups = QPushButton("Setup Dosyalarını İndir")
        self.btn_download_setups.setObjectName("downloadSetupsBtn")
        self.btn_download_setups.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download_setups.setToolTip("Seçilen programların kurulum (.exe / .msi) dosyalarını bir klasöre kaydeder.")
        self.btn_download_setups.clicked.connect(self._start_download_setups)
        self.btn_download_setups.setEnabled(False)
        row.addWidget(self.btn_download_setups)

        # Revert / Uninstall Tweaks Button (Active only in Tweaks tab)
        self.btn_revert_tweaks = QPushButton("Seçilen Ayarları Kaldır (Varsayılan)")
        self.btn_revert_tweaks.setObjectName("revertTweaksBtn")
        self.btn_revert_tweaks.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_revert_tweaks.setToolTip("Seçili kayıt defteri ayarlarını kaldırıp orijinal Windows varsayılanlarına döndürür.")
        self.btn_revert_tweaks.clicked.connect(self._revert_selected_tweaks)
        self.btn_revert_tweaks.hide()
        row.addWidget(self.btn_revert_tweaks)

        # Primary Action Button (Switches dynamically between Install & Apply Tweaks)
        self.btn_action = QPushButton("Seçilenleri Kur")
        self.btn_action.setObjectName("installBtn")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.clicked.connect(self._on_primary_action_clicked)
        row.addWidget(self.btn_action)

        layout.addLayout(row)
        return bar

    # =========================================================================
    # NAVIGATION & HUD UPDATES
    # =========================================================================

    def _on_splitter_moved(self, pos: int, index: int):
        """Automatically switch between slim rail and drawer if user drags the splitter handle."""
        if index == 1:
            if pos < 90 and not getattr(self, "is_sidebar_collapsed", False):
                self._toggle_sidebar(force_collapse=True)
            elif pos >= 150 and getattr(self, "is_sidebar_collapsed", False):
                self._toggle_sidebar(force_expand=True)

    def _toggle_sidebar(self, force_collapse: bool = False, force_expand: bool = False):
        """Toggle left sidebar between full drawer (220px) and slim rail (50px)."""
        if hasattr(self, "sidebar_container") and self.sidebar_container.isHidden():
            self.sidebar_container.show()
            self.is_sidebar_collapsed = True

        currently_collapsed = getattr(self, "is_sidebar_collapsed", False)
        if hasattr(self, "sidebar_drawer") and not self.sidebar_drawer.isVisible():
            currently_collapsed = True
        elif hasattr(self, "sidebar_container") and self.sidebar_container.width() <= 70:
            currently_collapsed = True

        if force_collapse:
            to_collapsed = True
        elif force_expand:
            to_collapsed = False
        else:
            to_collapsed = not currently_collapsed

        self.is_sidebar_collapsed = to_collapsed

        if to_collapsed:
            if hasattr(self, "sidebar_drawer"):
                self.sidebar_drawer.hide()
            if hasattr(self, "sidebar_rail"):
                self.sidebar_rail.show()
            if hasattr(self, "sidebar_container"):
                self.sidebar_container.setMinimumWidth(50)
                self.sidebar_container.setMaximumWidth(50)
            if hasattr(self, "main_splitter"):
                self.main_splitter.setSizes([50, max(200, self.width() - 50)])
        else:
            if hasattr(self, "sidebar_rail"):
                self.sidebar_rail.hide()
            if hasattr(self, "sidebar_drawer"):
                self.sidebar_drawer.show()
            if hasattr(self, "sidebar_container"):
                self.sidebar_container.setMinimumWidth(180)
                self.sidebar_container.setMaximumWidth(260)
            if hasattr(self, "main_splitter"):
                self.main_splitter.setSizes([220, max(200, self.width() - 220)])

        self._relayout_all_grids()

    def _switch_main_mode(self, mode: str):
        self.current_mode = mode

        # Update left tab button selection states
        buttons_to_update = [
            (getattr(self, "tab_btn_apps", None), mode == "apps"),
            (getattr(self, "tab_btn_tweaks", None), mode == "tweaks"),
            (getattr(self, "tab_btn_backup", None), mode == "backup"),
            (getattr(self, "btn_rail_apps", None), mode == "apps"),
            (getattr(self, "btn_rail_tweaks", None), mode == "tweaks"),
            (getattr(self, "btn_rail_backup", None), mode == "backup"),
            (getattr(self, "btn_settings_header", None), mode == "settings"),
        ]
        for btn, is_sel in buttons_to_update:
            if btn:
                btn.setProperty("selected", "true" if is_sel else "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        if mode == "apps":
            self.stack.setCurrentIndex(0)
            self.btn_action.setText("Seçilenleri Kur")
            if hasattr(self, "btn_download_setups"):
                self.btn_download_setups.show()
            if hasattr(self, "btn_revert_tweaks"):
                self.btn_revert_tweaks.hide()
            if PACKAGES:
                self._update_app_hud(PACKAGES[0])
        elif mode == "tweaks":
            self.stack.setCurrentIndex(1)
            self.btn_action.setText("Seçilen Ayarları Uygula")
            if hasattr(self, "btn_download_setups"):
                self.btn_download_setups.hide()
            if hasattr(self, "btn_revert_tweaks"):
                self.btn_revert_tweaks.show()
            self._refresh_tweak_statuses()
            if TWEAKS:
                self._update_tweak_hud(TWEAKS[0])
        elif mode == "backup":
            self.stack.setCurrentIndex(2)
            if hasattr(self, "btn_download_setups"):
                self.btn_download_setups.hide()
            if hasattr(self, "btn_revert_tweaks"):
                self.btn_revert_tweaks.hide()
            if self.backup_mode_operation == "backup":
                self.btn_action.setText("Seçilenleri Klasöre Yedekle")
            else:
                self.btn_action.setText("Yedekten Sisteme Geri Yükle")
            self._refresh_backup_statuses()
            if BACKUP_ITEMS:
                self._on_backup_hovered(BACKUP_ITEMS[0])
        elif mode == "settings":
            self.stack.setCurrentIndex(3)
            self.btn_action.setText("Ayarlar Aktif")
            if hasattr(self, "btn_download_setups"):
                self.btn_download_setups.hide()
            if hasattr(self, "btn_revert_tweaks"):
                self.btn_revert_tweaks.hide()
            self._update_settings_profile_stats()

        self._update_counter()

    def _on_card_hovered(self, pkg: dict):
        self._update_app_hud(pkg)

    def _update_app_hud(self, pkg: dict):
        self.current_pkg = pkg
        self.inspect_badge.setProperty("class", "")
        self.inspect_cat_lbl.setProperty("class", "")
        self.inspect_hint_lbl.setProperty("class", "")
        self.inspect_badge.setStyleSheet("")
        self.inspect_cat_lbl.setStyleSheet("")
        self.inspect_hint_lbl.setStyleSheet("")
        self.inspect_badge.setText("PROGRAM BİLGİSİ")
        self.inspect_title.setText(pkg["name"])
        self.inspect_cat_lbl.setText(f"[{pkg['category'].upper()}]")
        self.inspect_desc.setText(pkg["full_desc"])
        self.inspect_source_lbl.setText(f"Paket ID: {pkg['winget_id']}")
        self.inspect_hint_lbl.setText("[Sağ Tık: Resmi Site]")
        for w in (self.inspect_badge, self.inspect_cat_lbl, self.inspect_hint_lbl):
            w.style().unpolish(w)
            w.style().polish(w)

    def _on_tweak_hovered(self, tweak: dict):
        self._update_tweak_hud(tweak)

    def _update_tweak_hud(self, tweak: dict):
        self.current_tweak = tweak
        self.inspect_badge.setProperty("class", "")
        self.inspect_cat_lbl.setProperty("class", "")
        self.inspect_hint_lbl.setProperty("class", "")
        self.inspect_badge.setStyleSheet("")
        self.inspect_cat_lbl.setStyleSheet("")
        self.inspect_hint_lbl.setStyleSheet("")
        self.inspect_badge.setText("REGEDIT AYARI")
        self.inspect_title.setText(tweak["name"])
        self.inspect_cat_lbl.setText(f"[{tweak['category'].upper()}]")
        self.inspect_desc.setText(tweak["full_desc"])
        key_meta = tweak.get("reg_key") or tweak.get("command") or ""
        self.inspect_source_lbl.setText(f"Ayar: {key_meta}")
        self.inspect_hint_lbl.setText("[Kayıt Defteri]")
        for w in (self.inspect_badge, self.inspect_cat_lbl, self.inspect_hint_lbl):
            w.style().unpolish(w)
            w.style().polish(w)

    def _on_pkg_website_opened(self, pkg: dict):
        url = pkg.get("website") or pkg.get("url", "")
        self.current_pkg = pkg
        self.inspect_badge.setText("RESMİ WEB SİTESİ")
        self.inspect_badge.setProperty("class", "inspectBadgeSuccess")
        self.inspect_title.setText(f"{pkg['name']} (Resmi Sayfa)")
        self.inspect_cat_lbl.setText("[WEB TARAYICI]")
        self.inspect_cat_lbl.setProperty("class", "inspectCatSuccess")
        self.inspect_desc.setText(f"Resmi indirme ve destek sayfası varsayılan tarayıcınızda açıldı:\n{url}")
        self.inspect_source_lbl.setText(f"URL: {url}")
        self.inspect_hint_lbl.setText("[Tarayıcıda Açıldı]")
        self.inspect_hint_lbl.setProperty("class", "inspectHintSuccess")
        self.inspect_badge.setStyleSheet("")
        self.inspect_cat_lbl.setStyleSheet("")
        self.inspect_hint_lbl.setStyleSheet("")
        for w in (self.inspect_badge, self.inspect_cat_lbl, self.inspect_hint_lbl):
            w.style().unpolish(w)
            w.style().polish(w)
        self._append_log(f"[WEB] {pkg['name']} resmi sayfası tarayıcıda açıldı: {url}")

    def _append_log(self, text: str):
        if hasattr(self, "terminal_console"):
            self.terminal_console.append(text)
            cursor = self.terminal_console.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.terminal_console.setTextCursor(cursor)

    def _on_card_toggled(self, pkg: dict, checked: bool):
        self._update_app_hud(pkg)
        self._update_counter()
        self._save_live_profile_state()

    def _on_tweak_toggled(self, tweak: dict, checked: bool):
        self._update_tweak_hud(tweak)
        self._update_counter()
        self._save_live_profile_state()

    def _update_counter(self):
        if self.current_mode == "apps":
            selected_count = sum(1 for c in self.app_cards.values() if c.is_selected())
            total_count = len(self.app_cards)
            self.counter_lbl.setText(f"Seçilen: {selected_count} / {total_count} Program")
            self.btn_action.setEnabled(selected_count > 0)
            if hasattr(self, "btn_download_setups"):
                self.btn_download_setups.setEnabled(selected_count > 0)
        elif self.current_mode == "tweaks":
            selected_count = sum(1 for c in self.tweak_cards.values() if c.is_selected())
            active_count = sum(1 for c in self.tweak_cards.values() if c.is_active)
            total_count = len(self.tweak_cards)
            self.counter_lbl.setText(f"Seçilen: {selected_count} / {total_count} Ayar (Aktif: {active_count})")
            self.btn_action.setEnabled(selected_count > 0)
            if hasattr(self, "btn_revert_tweaks"):
                self.btn_revert_tweaks.setEnabled(selected_count > 0 or active_count > 0)
        elif self.current_mode == "backup":
            selected_count = sum(1 for c in self.backup_cards.values() if c.is_selected())
            total_count = len(self.backup_cards)
            self.counter_lbl.setText(f"Seçilen: {selected_count} / {total_count} Ayar Öğesi")
            self.btn_action.setEnabled(selected_count > 0)
        elif self.current_mode == "settings":
            self.counter_lbl.setText("Görünüm ve Profil Ayarları")
            self.btn_action.setEnabled(False)

        # Smart Toggle for Apps
        if hasattr(self, "btn_toggle_select_apps"):
            visible_cards = [c for c in self.app_cards.values() if not c.isHidden()]
            app_selected = sum(1 for c in visible_cards if c.is_selected())
            app_total = len(visible_cards)
            if app_selected == app_total and app_total > 0:
                self.btn_toggle_select_apps.setText("Temizle")
                self.btn_toggle_select_apps.setObjectName("clearBtn")
            else:
                self.btn_toggle_select_apps.setText("Tümünü Seç")
                self.btn_toggle_select_apps.setObjectName("")
            self.btn_toggle_select_apps.style().unpolish(self.btn_toggle_select_apps)
            self.btn_toggle_select_apps.style().polish(self.btn_toggle_select_apps)

        # Smart Toggle for Tweaks (All & Active)
        if hasattr(self, "btn_toggle_select_tweaks"):
            tweak_selected = sum(1 for c in self.tweak_cards.values() if c.is_selected())
            tweak_total = len(self.tweak_cards)
            if tweak_selected == tweak_total and tweak_total > 0:
                self.btn_toggle_select_tweaks.setText("Temizle")
                self.btn_toggle_select_tweaks.setObjectName("clearBtn")
            else:
                self.btn_toggle_select_tweaks.setText("Tümünü Seç")
                self.btn_toggle_select_tweaks.setObjectName("")
            self.btn_toggle_select_tweaks.style().unpolish(self.btn_toggle_select_tweaks)
            self.btn_toggle_select_tweaks.style().polish(self.btn_toggle_select_tweaks)

        if hasattr(self, "btn_active_tweaks"):
            active_cards = [c for c in self.tweak_cards.values() if c.is_active]
            if active_cards and all(c.is_selected() for c in active_cards):
                self.btn_active_tweaks.setText("Kurulu Seçimini Kaldır")
                self.btn_active_tweaks.setObjectName("clearBtn")
            else:
                count_str = f" ({len(active_cards)})" if active_cards else ""
                self.btn_active_tweaks.setText(f"Kurulu Olanları Seç{count_str}")
                self.btn_active_tweaks.setObjectName("")
            self.btn_active_tweaks.style().unpolish(self.btn_active_tweaks)
            self.btn_active_tweaks.style().polish(self.btn_active_tweaks)

        # Smart Toggle for Backup
        if hasattr(self, "btn_toggle_select_backup"):
            backup_selected = sum(1 for c in self.backup_cards.values() if c.is_selected())
            backup_total = len(self.backup_cards)
            if backup_selected == backup_total and backup_total > 0:
                self.btn_toggle_select_backup.setText("Temizle")
                self.btn_toggle_select_backup.setObjectName("clearBtn")
            else:
                self.btn_toggle_select_backup.setText("Tümünü Seç")
                self.btn_toggle_select_backup.setObjectName("")
            self.btn_toggle_select_backup.style().unpolish(self.btn_toggle_select_backup)
            self.btn_toggle_select_backup.style().polish(self.btn_toggle_select_backup)

        # Smart Preset Combo active state (Software tab)
        if hasattr(self, "preset_combo"):
            active_preset = ""
            for p_key in ["essential", "dev", "database", "gamer", "ai", "hardware"]:
                p_pkgs = [p for p in PACKAGES if p_key in p.get("presets", [])]
                if p_pkgs and all(self.app_cards[p["id"]].is_selected() for p in p_pkgs):
                    active_preset = p_key
                    break
            self._is_updating_preset_combo = True
            idx = self.preset_combo.findData(active_preset)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
            else:
                self.preset_combo.setCurrentIndex(0)
            self._is_updating_preset_combo = False

        # Smart Recommended Button active state (Tweaks tab)
        if hasattr(self, "btn_rec_tweaks"):
            rec_tweaks = [t for t in TWEAKS if t.get("recommended", False)]
            is_rec_active = len(rec_tweaks) > 0 and all(self.tweak_cards[t["id"]].is_selected() for t in rec_tweaks)
            self.btn_rec_tweaks.setProperty("selected", "true" if is_rec_active else "false")
            self.btn_rec_tweaks.style().unpolish(self.btn_rec_tweaks)
            self.btn_rec_tweaks.style().polish(self.btn_rec_tweaks)

    # =========================================================================
    # APP FILTERS & SELECTION
    # =========================================================================

    def _switch_app_category(self, cat_id: str):
        self.current_app_category = cat_id
        if hasattr(self, "app_category_buttons"):
            for c_id, btn in self.app_category_buttons.items():
                btn.setProperty("selected", "true" if c_id == cat_id else "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        self._filter_app_cards()

    def _on_app_search_changed(self, text: str):
        self.search_filter = text.lower().strip()
        self._filter_app_cards()

    def _filter_app_cards(self):
        while self.app_grid.count():
            self.app_grid.takeAt(0)

        cols = getattr(self, "_app_grid_cols", 1)
        visible_idx = 0
        for pkg in PACKAGES:
            card = self.app_cards.get(pkg["id"])
            if not card:
                continue

            # When search text is active, search across ALL categories ignoring current category filter
            if self.search_filter:
                match_cat = True
            elif self.current_app_category == "installed":
                match_cat = getattr(card, "is_installed", False)
            else:
                match_cat = (self.current_app_category == "all" or pkg["category"] == self.current_app_category)

            match_search = (
                not self.search_filter or
                self.search_filter in pkg["name"].lower() or
                self.search_filter in pkg["short_desc"].lower() or
                self.search_filter in pkg.get("full_desc", "").lower() or
                self.search_filter in pkg["winget_id"].lower()
            )
            is_visible = match_cat and match_search
            card.setVisible(is_visible)

            if is_visible:
                row = visible_idx // cols
                col = visible_idx % cols
                self.app_grid.addWidget(card, row, col)
                visible_idx += 1

    def _apply_app_preset(self, preset_name: str):
        preset_pkgs = [pkg for pkg in PACKAGES if preset_name in pkg.get("presets", [])]
        if not preset_pkgs:
            return

        # Ensure all cards are visible so user sees the preset items immediately
        if self.current_app_category != "all":
            self._switch_app_category("all")
        if self.search_filter:
            self.app_search_box.clear()

        preset_ids = {p["id"] for p in preset_pkgs}
        all_selected = all(self.app_cards[pid].is_selected() for pid in preset_ids)

        if all_selected:
            # Preset is currently active -> toggle off: deselect all preset items
            for pid in preset_ids:
                self.app_cards[pid].set_selected(False)
        else:
            # Preset is not active -> select this preset exclusively
            for pkg in PACKAGES:
                self.app_cards[pkg["id"]].set_selected(pkg["id"] in preset_ids)

        self._update_counter()
        self._save_live_profile_state()

    def _handle_select_all_shortcut(self):
        """Ctrl+A handler: if editing text in search or input box, select text;
        otherwise toggle selection of all visible items in the active category/tab."""
        focus_w = QApplication.focusWidget()
        if isinstance(focus_w, (QLineEdit, QTextEdit)):
            focus_w.selectAll()
            return

        if self.current_mode == "apps":
            self._toggle_select_apps()
        elif self.current_mode == "tweaks":
            self._toggle_select_tweaks()
        elif self.current_mode == "backup":
            self._toggle_select_backup()

    def _toggle_select_apps(self):
        visible_cards = [c for c in self.app_cards.values() if not c.isHidden()]
        if not visible_cards:
            return
        all_selected = all(c.is_selected() for c in visible_cards)
        if all_selected:
            self._clear_all_apps()
        else:
            self._select_all_apps()

    def _select_all_apps(self):
        visible_cards = [c for c in self.app_cards.values() if not c.isHidden()]
        for card in visible_cards:
            card.set_selected(True)
        self._update_counter()
        self._save_live_profile_state()

    def _clear_all_apps(self):
        visible_cards = [c for c in self.app_cards.values() if not c.isHidden()]
        for card in visible_cards:
            card.set_selected(False)
        self._update_counter()
        self._save_live_profile_state()

    # =========================================================================
    # TWEAK FILTERS & SELECTION
    # =========================================================================

    def _on_tweak_search_changed(self, text: str):
        filter_text = text.lower().strip()
        while self.tweaks_grid.count():
            self.tweaks_grid.takeAt(0)

        visible_idx = 0
        for tweak in TWEAKS:
            card = self.tweak_cards[tweak["id"]]
            match_search = (
                not filter_text or
                filter_text in tweak["name"].lower() or
                filter_text in tweak["short_desc"].lower()
            )
            card.setVisible(match_search)

            if match_search:
                row = visible_idx // 3
                col = visible_idx % 3
                self.tweaks_grid.addWidget(card, row, col)
                visible_idx += 1

    def _filter_tweak_cards(self):
        self._on_tweak_search_changed(self.tweak_search_box.text())

    def _select_recommended_tweaks(self):
        rec_tweaks = [t for t in TWEAKS if t.get("recommended", False)]
        if not rec_tweaks:
            return
        all_rec_selected = all(self.tweak_cards[t["id"]].is_selected() for t in rec_tweaks)
        new_state = not all_rec_selected
        for tweak in rec_tweaks:
            self.tweak_cards[tweak["id"]].set_selected(new_state)
        self._update_counter()
        self._save_live_profile_state()

    def _select_active_tweaks(self):
        active_cards = [c for c in self.tweak_cards.values() if c.is_active]
        if not active_cards:
            QMessageBox.information(
                self,
                "Kurulu Ayar Yok",
                "Şu anda sisteminizde [Aktif] olarak tespit edilen bir kayıt defteri ayarı bulunmuyor."
            )
            return
        all_active_selected = all(c.is_selected() for c in active_cards)
        new_state = not all_active_selected
        for card in active_cards:
            card.set_selected(new_state)
        self._update_counter()
        self._save_live_profile_state()

    def _toggle_select_tweaks(self):
        all_selected = (len(self.tweak_cards) > 0 and all(c.is_selected() for c in self.tweak_cards.values()))
        if all_selected:
            self._clear_all_tweaks()
        else:
            self._select_all_tweaks()

    def _select_all_tweaks(self):
        for card in self.tweak_cards.values():
            card.set_selected(True)
        self._update_counter()
        self._save_live_profile_state()

    def _clear_all_tweaks(self):
        for card in self.tweak_cards.values():
            card.set_selected(False)
        self._update_counter()
        self._save_live_profile_state()

    def _refresh_tweak_statuses(self):
        for card in self.tweak_cards.values():
            card.refresh_status()
        self._update_counter()

    def _restart_explorer_action(self):
        reply = QMessageBox.question(
            self,
            "Gezgini Yeniden Başlat",
            "Windows Gezgini (explorer.exe) yeniden başlatılsın mı?\n"
            "Ekranınız 1 saniyeliğine yenilenecektir.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            restart_explorer()

    # =========================================================================
    # BACKUP & RESTORE CONTROLS
    # =========================================================================

    def _set_backup_operation(self, mode: str):
        self.backup_mode_operation = mode
        self.btn_op_backup.setProperty("selected", "true" if mode == "backup" else "false")
        self.btn_op_restore.setProperty("selected", "true" if mode == "restore" else "false")
        self.btn_op_backup.style().unpolish(self.btn_op_backup)
        self.btn_op_backup.style().polish(self.btn_op_backup)
        self.btn_op_restore.style().unpolish(self.btn_op_restore)
        self.btn_op_restore.style().polish(self.btn_op_restore)

        if mode == "backup":
            self.btn_action.setText("Seçilenleri Klasöre Yedekle")
        else:
            self.btn_action.setText("Yedekten Sisteme Geri Yükle")

        self._refresh_backup_statuses()
        self._update_counter()

    def _browse_backup_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Yedekleme Klasörünü Seçin", self.backup_dir
        )
        if directory:
            self.backup_dir = directory
            self.backup_dir_input.setText(directory)
            self._refresh_backup_statuses()

    def _on_backup_dir_input_changed(self, text: str):
        self.backup_dir = text.strip()
        self._refresh_backup_statuses()
        self._save_live_profile_state()

    def _open_backup_folder_in_explorer(self):
        target = self.backup_dir
        if not os.path.exists(target):
            try:
                os.makedirs(target, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Klasör oluşturulamadı: {e}")
                return
        os.startfile(target)

    def _refresh_backup_statuses(self):
        for card in self.backup_cards.values():
            card.update_status(self.backup_mode_operation, self.backup_dir)
        self._update_counter()

    def _toggle_select_backup(self):
        all_selected = (len(self.backup_cards) > 0 and all(c.is_selected() for c in self.backup_cards.values()))
        if all_selected:
            for c in self.backup_cards.values():
                c.set_selected(False)
        else:
            for c in self.backup_cards.values():
                c.set_selected(True)
        self._update_counter()
        self._save_live_profile_state()

    def _on_backup_hovered(self, item: dict):
        self.current_backup_item = item
        self.inspect_badge.setProperty("class", "")
        self.inspect_cat_lbl.setProperty("class", "")
        self.inspect_hint_lbl.setProperty("class", "")
        self.inspect_badge.setStyleSheet("")
        self.inspect_cat_lbl.setStyleSheet("")
        self.inspect_hint_lbl.setStyleSheet("")
        self.inspect_badge.setText("YEDEK & RESTORE")
        self.inspect_title.setText(item["name"])
        self.inspect_cat_lbl.setText("[AYAR TRANSFERİ]")
        self.inspect_desc.setText(item["full_desc"])
        self.inspect_source_lbl.setText(f"Modül: {item['id']}")
        self.inspect_hint_lbl.setText("[Format Öncesi/Sonrası]")
        for w in (self.inspect_badge, self.inspect_cat_lbl, self.inspect_hint_lbl):
            w.style().unpolish(w)
            w.style().polish(w)

    def _on_backup_toggled(self, item: dict, checked: bool):
        self._on_backup_hovered(item)
        self._update_counter()
        self._save_live_profile_state()

    # =========================================================================
    # ACTIONS (INSTALL, APPLY TWEAKS, OR BACKUP/RESTORE)
    # =========================================================================

    def _on_primary_action_clicked(self):
        if self.current_mode == "apps":
            self._start_installation()
        elif self.current_mode == "tweaks":
            self._apply_selected_tweaks()
        elif self.current_mode == "backup":
            self._start_backup_restore()
        elif self.current_mode == "settings":
            pass

    def _apply_selected_tweaks(self):
        selected_tweaks = [t for t in TWEAKS if self.tweak_cards[t["id"]].is_selected()]
        if not selected_tweaks:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir Windows ayarı seçin!")
            return

        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Yönetici İzni Gerekli",
                "Bazı kayıt defteri ayarları (260 karakter sınırı, UAC, hazırda bekletme) yönetici izni gerektirir.\n"
                "Uygulama yönetici haklarıyla yeniden başlatılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                restart_as_admin()
                return

        applied_count = 0
        failed_count = 0
        needs_explorer = False

        self.terminal_console.show()
        self.btn_terminal.setText("Konsolu Gizle")
        self.terminal_console.clear()
        self._append_log("=== WINDOWS REGEDIT İNCE AYARLARI UYGULANIYOR ===")

        for tweak in selected_tweaks:
            card = self.tweak_cards[tweak["id"]]
            success, msg = apply_tweak(tweak)
            card.set_applied_status(success, msg)
            if success:
                applied_count += 1
                self._append_log(f"[BAŞARILI] {tweak['name']} -> {msg}")
                if tweak.get("needs_explorer_restart"):
                    needs_explorer = True
            else:
                failed_count += 1
                self._append_log(f"[HATA] {tweak['name']} -> {msg}")

        self._update_counter()

        # Prompt to restart explorer if context menu or file extension tweaks were applied
        if needs_explorer:
            reply = QMessageBox.question(
                self,
                "Ayarlar Uygulandı",
                f"{applied_count} Windows ayarı başarıyla uygulandı!\n\n"
                "Klasik sağ tık menüsü ve dosya uzantılarının hemen aktif olması için Windows Gezgini'ni şimdi yeniden başlatmak ister misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                restart_explorer()
        else:
            QMessageBox.information(
                self,
                "Ayarlar Uygulandı",
                f"{applied_count} Windows ayarı başarıyla uygulandı!"
            )

    def _revert_selected_tweaks(self):
        selected_tweaks = [t for t in TWEAKS if self.tweak_cards[t["id"]].is_selected()]

        # If none selected, offer to revert all currently active tweaks
        if not selected_tweaks:
            active_tweaks = [t for t in TWEAKS if self.tweak_cards[t["id"]].is_active]
            if not active_tweaks:
                QMessageBox.warning(
                    self,
                    "Uyarı",
                    "Kaldırmak için lütfen listeden en az bir ayar seçin veya sistemde aktif ayar bulunmuyor."
                )
                return
            reply = QMessageBox.question(
                self,
                "Aktif Ayarları Kaldır",
                f"Şu anda herhangi bir ayar seçmediniz.\n\n"
                f"Sisteminizde [Aktif] olan {len(active_tweaks)} adet ayarın tümünü kaldırıp orijinal Windows varsayılanlarına döndürmek ister misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                selected_tweaks = active_tweaks
            else:
                return

        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Yönetici İzni Gerekli",
                "Kayıt defteri ayarlarını varsayılana döndürmek yönetici izni gerektirir.\n"
                "Uygulama yönetici haklarıyla yeniden başlatılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                restart_as_admin()
                return

        reply = QMessageBox.question(
            self,
            "Ayarları Kaldırma Onayı",
            f"Seçilen {len(selected_tweaks)} Windows ayarı kaldırılacak ve orijinal sistem varsayılanlarına döndürülecektir.\n\n"
            "İşlemi onaylıyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        reverted_count = 0
        failed_count = 0
        needs_explorer = False

        self.terminal_console.show()
        self.btn_terminal.setText("Konsolu Gizle")
        self.terminal_console.clear()
        self._append_log("=== WINDOWS REGEDIT İNCE AYARLARI KALDIRILIYOR / VARSAYILANA DÖNDÜRÜLÜYOR ===")

        for tweak in selected_tweaks:
            card = self.tweak_cards[tweak["id"]]
            success, msg = revert_tweak(tweak)
            card.set_reverted_status(success, msg)
            if success:
                reverted_count += 1
                self._append_log(f"[KALDIRILDI] {tweak['name']} -> {msg}")
                if tweak.get("needs_explorer_restart"):
                    needs_explorer = True
            else:
                failed_count += 1
                self._append_log(f"[HATA] {tweak['name']} -> {msg}")

        self._update_counter()

        if needs_explorer:
            reply = QMessageBox.question(
                self,
                "Ayarlar Kaldırıldı",
                f"{reverted_count} Windows ayarı başarıyla kaldırıldı ve varsayılana döndürüldü!\n\n"
                "Değişikliklerin anında geçerli olması için Windows Gezgini'ni şimdi yeniden başlatmak ister misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                restart_explorer()
        else:
            QMessageBox.information(
                self,
                "Ayarlar Kaldırıldı",
                f"{reverted_count} Windows ayarı başarıyla kaldırıldı ve varsayılana döndürüldü!"
            )

    def _start_installed_scan(self):
        self.scanner = InstalledScanner()
        self.scanner.scan_complete.connect(self._on_scan_complete)
        self.scanner.start()

    def _on_scan_complete(self, installed_ids: set):
        self.installed_ids = installed_ids
        for pkg in PACKAGES:
            card = self.app_cards.get(pkg["id"])
            if card:
                w_id = pkg.get("winget_id", "").lower()
                is_inst = bool(w_id and w_id in installed_ids)
                if not is_inst:
                    for fid in pkg.get("fallback_winget_ids", []):
                        if fid.lower() in installed_ids:
                            is_inst = True
                            break
                if is_inst:
                    card.set_installed_status(True)
        if getattr(self, "current_app_category", "") == "installed":
            self._filter_app_cards()

    def _elevate_admin(self):
        reply = QMessageBox.question(
            self,
            "Yönetici İzni",
            "Uygulama yönetici haklarıyla yeniden başlatılsın mı?\n"
            "(DirectX, VC++ ve Regedit ayarları için tavsiye edilir)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            restart_as_admin()

    def _toggle_terminal(self):
        if self.terminal_console.isVisible():
            self.terminal_console.hide()
            self.btn_terminal.setText("Konsol Günlüğü")
        else:
            self.terminal_console.show()
            self.btn_terminal.setText("Konsolu Gizle")

    def _load_active_profile_into_ui(self):
        active = self.profile_mgr.get_active_profile()
        self._switch_to_profile(active["id"])

    def _show_browser_profile_menu(self):
        menu = QMenu(self)

        active_prof = self.profile_mgr.get_active_profile()
        title_action = menu.addAction(f"KULLANICI PROFİLLERİ — Aktif: {active_prof['name']}")
        title_action.setEnabled(False)
        menu.addSeparator()

        for prof in self.profile_mgr.get_all_profiles():
            is_active = (prof["id"] == self.profile_mgr.active_profile_id)
            checkmark = "✓ " if is_active else "     "
            apps_c = len(prof.get("apps", []))
            tweaks_c = len(prof.get("tweaks", []))
            backups_c = len(prof.get("backups", []))
            item_text = f"{checkmark}{prof['name']}   [{apps_c} Program, {tweaks_c} Ayar, {backups_c} Yedek]"
            action = menu.addAction(item_text)
            action.triggered.connect(lambda _, pid=prof["id"]: QTimer.singleShot(0, lambda p=pid: self._switch_to_profile(p)))

        menu.addSeparator()

        act_add = menu.addAction("Yeni Profil Ekle (Sifirdan Basla)")
        act_add.triggered.connect(lambda: QTimer.singleShot(0, self._add_new_browser_profile))

        act_rename = menu.addAction("Aktif Profili Yeniden Adlandir...")
        act_rename.triggered.connect(lambda: QTimer.singleShot(0, self._rename_active_browser_profile))

        act_clear = menu.addAction("Bu Profildeki Secimleri Sifirla")
        act_clear.triggered.connect(lambda: QTimer.singleShot(0, self._clear_active_browser_profile))

        menu.addSeparator()

        act_export = menu.addAction("Bu Profili USB / Diske Aktar (.json)...")
        act_export.triggered.connect(lambda: QTimer.singleShot(0, self._export_active_browser_profile))

        act_import = menu.addAction("USB / Diskten Profil Yukle (.json)...")
        act_import.triggered.connect(lambda: QTimer.singleShot(0, self._import_browser_profile))

        if len(self.profile_mgr.get_all_profiles()) > 1:
            menu.addSeparator()
            act_delete = menu.addAction("Bu Profili Sil")
            act_delete.triggered.connect(lambda: QTimer.singleShot(0, self._delete_active_browser_profile))

        menu.exec(self.btn_profile_switcher.mapToGlobal(self.btn_profile_switcher.rect().bottomLeft()))

    def _toggle_theme(self):
        """Toggles between Dark Mode (Gece Modu) and Light Mode (Gündüz Modu)."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new_theme)

    def _apply_theme(self, theme: str):
        """Applies theme stylesheet, updates toggle button, card tooltips, and repolishes UI."""
        self.current_theme = theme
        self.profile_mgr.set_theme(theme)

        # Apply global stylesheet to application
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(theme))

        # Update theme toggle button
        if hasattr(self, "btn_theme_toggle"):
            if theme == "light":
                self.btn_theme_toggle.setText("Gece Modu")
            else:
                self.btn_theme_toggle.setText("Gunduz Modu")

        # Update all cards for theme-specific tooltips and state repolish
        for card in self.app_cards.values():
            card.update_theme(theme)
        for card in self.tweak_cards.values():
            card.update_theme(theme)
        for card in self.backup_cards.values():
            card.update_theme(theme)

        # Repolish all key widgets
        widgets_to_repolish = [
            self,
            getattr(self, "inspect_panel", None),
            getattr(self, "inspect_badge", None),
            getattr(self, "inspect_cat_lbl", None),
            getattr(self, "inspect_title", None),
            getattr(self, "inspect_desc", None),
            getattr(self, "inspect_hint_lbl", None),
            getattr(self, "btn_theme_toggle", None),
            getattr(self, "btn_profile_switcher", None),
        ]
        for w in widgets_to_repolish:
            if w is not None:
                w.style().unpolish(w)
                w.style().polish(w)

        # Refresh active HUD item
        if self.current_mode == "apps" and hasattr(self, "current_pkg") and self.current_pkg:
            self._update_app_hud(self.current_pkg)
        elif self.current_mode == "tweaks" and hasattr(self, "current_tweak") and self.current_tweak:
            self._update_tweak_hud(self.current_tweak)
        elif self.current_mode == "backup" and hasattr(self, "current_backup_item") and self.current_backup_item:
            self._on_backup_hovered(self.current_backup_item)

        # Update tab and sidebar navigation icons to monochrome theme-matched vectors
        self._update_sidebar_icons(theme)

    def _switch_to_profile(self, profile_id: str):
        prof = self.profile_mgr.get_profile(profile_id)
        if not prof:
            return

        self._is_switching_profile = True
        try:
            self.profile_mgr.set_active_profile_id(profile_id)
            sel_apps = set(prof.get("apps", []))
            sel_tweaks = set(prof.get("tweaks", []))
            sel_backups = set(prof.get("backups", []))
            if "winget_manifest" in sel_backups:
                sel_backups.add("installed_apps")

            for pkg in PACKAGES:
                card = self.app_cards.get(pkg["id"])
                if card:
                    is_sel = (pkg["id"] in sel_apps) or getattr(card, "is_installed", False)
                    card.checkbox.blockSignals(True)
                    card.set_selected(is_sel)
                    card.setProperty("checked", "true" if is_sel else "false")
                    card.style().unpolish(card)
                    card.style().polish(card)
                    card.checkbox.blockSignals(False)

            for tweak in TWEAKS:
                card = self.tweak_cards.get(tweak["id"])
                if card:
                    is_sel = (tweak["id"] in sel_tweaks) or getattr(card, "is_active", False)
                    card.checkbox.blockSignals(True)
                    card.set_selected(is_sel)
                    card.setProperty("checked", "true" if is_sel else "false")
                    card.style().unpolish(card)
                    card.style().polish(card)
                    card.checkbox.blockSignals(False)

            for item in BACKUP_ITEMS:
                card = self.backup_cards.get(item["id"])
                if card:
                    is_sel = (item["id"] in sel_backups) or getattr(card, "is_available", False)
                    card.checkbox.blockSignals(True)
                    card.set_selected(is_sel)
                    card.setProperty("checked", "true" if is_sel else "false")
                    card.style().unpolish(card)
                    card.style().polish(card)
                    card.checkbox.blockSignals(False)

            default_backup = r"D:\Keystone_Yedek" if os.path.exists("D:\\") else os.path.join(
                os.environ.get("USERPROFILE", os.path.expanduser("~")), "Documents", "Keystone_Yedek"
            )
            self.backup_dir = prof.get("backup_dir") or default_backup
            if hasattr(self, "backup_dir_input"):
                self.backup_dir_input.blockSignals(True)
                self.backup_dir_input.setText(self.backup_dir)
                self.backup_dir_input.blockSignals(False)

            self._update_profile_switcher_button()
            self._update_counter()
            self._refresh_profile_combo()
            self._update_settings_profile_stats()
        finally:
            self._is_switching_profile = False

    def _save_live_profile_state(self):
        if getattr(self, "_is_switching_profile", False):
            return
        sel_apps = [p["id"] for p in PACKAGES if self.app_cards[p["id"]].is_selected()]
        sel_tweaks = [t["id"] for t in TWEAKS if self.tweak_cards[t["id"]].is_selected()]
        sel_backups = [b["id"] for b in BACKUP_ITEMS if self.backup_cards[b["id"]].is_selected()]
        self.profile_mgr.update_active_selections(
            apps=sel_apps,
            tweaks=sel_tweaks,
            backups=sel_backups,
            backup_dir=self.backup_dir
        )
        self._update_profile_switcher_button()

    def _update_profile_switcher_button(self):
        if not hasattr(self, "btn_profile_switcher"):
            return
        active_prof = self.profile_mgr.get_active_profile()
        app_count = len(active_prof.get("apps", []))
        tweak_count = len(active_prof.get("tweaks", []))
        backup_count = len(active_prof.get("backups", []))
        total_items = app_count + tweak_count + backup_count

        self.btn_profile_switcher.setText(
            f"Profil: {active_prof['name']} ({total_items} Secili) ▼"
        )

    def _add_new_browser_profile(self):
        existing = [p["name"] for p in self.profile_mgr.get_all_profiles()]
        dlg = AddProfileDialog(existing, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_prof = self.profile_mgr.create_new_profile(dlg.selected_name, dlg.selected_icon)
            self._switch_to_profile(new_prof["id"])
            QMessageBox.information(
                self,
                "Yeni Profil Oluşturuldu",
                f"'{new_prof['name']}' profili başarıyla oluşturuldu!\n\n"
                "Bu profil tamamen sıfırdan başlatıldı.\n"
                "Seçeceğiniz tüm programlar, ayarlar ve yedekler "
                "bu profile özel olarak otomatik kaydedilecektir."
            )

    def _rename_active_browser_profile(self):
        active = self.profile_mgr.get_active_profile()
        dlg = RenameProfileDialog(active["name"], self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_name = dlg.new_name.strip()
            if new_name:
                self.profile_mgr.rename_profile(active["id"], new_name)
                self._update_profile_switcher_button()
                self._refresh_profile_combo()
                self._update_settings_profile_stats()

    def _clear_active_browser_profile(self):
        active = self.profile_mgr.get_active_profile()
        reply = QMessageBox.question(
            self,
            "Seçimleri Sıfırla",
            f"'{active['name']}' profilindeki tüm seçimler temizlenecek ve profil sıfırdan başlama durumuna döndürülecektir.\n\nEmin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.profile_mgr.clear_profile_selections(active["id"])
            self._switch_to_profile(active["id"])

    def _delete_active_browser_profile(self):
        all_profs = self.profile_mgr.get_all_profiles()
        if len(all_profs) <= 1:
            QMessageBox.warning(self, "Uyarı", "Son kalan profili silemezsiniz! En az bir profil bulunmalıdır.")
            return

        active = self.profile_mgr.get_active_profile()
        reply = QMessageBox.question(
            self,
            "Profili Sil",
            f"'{active['name']}' profilini kalıcı olarak silmek istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted_id = active["id"]
            self.profile_mgr.delete_profile(deleted_id)
            next_active = self.profile_mgr.get_active_profile()
            self._switch_to_profile(next_active["id"])
            QMessageBox.information(self, "Silindi", f"'{active['name']}' profili silindi. '{next_active['name']}' profiline geçildi.")

    def _export_active_browser_profile(self):
        active = self.profile_mgr.get_active_profile()
        clean_name = "".join(c for c in active["name"] if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_").lower()
        default_file = f"format_profil_{clean_name}.json" if clean_name else "format_profil.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Profili USB / Diske Aktar",
            default_file,
            "JSON Dosyaları (*.json)"
        )
        if file_path:
            success = self.profile_mgr.export_profile_to_file(active["id"], file_path)
            if success:
                QMessageBox.information(
                    self,
                    "Dışa Aktarma Başarılı",
                    f"'{active['name']}' profili başarıyla USB / diske aktarıldı:\n{file_path}\n\n"
                    "Format sonrası bu dosyayı 'USB'den Profil Yükle' seçeneği ile tek tıkla geri yükleyebilirsiniz."
                )
            else:
                QMessageBox.critical(self, "Hata", "Profil dosyası yazılamadı!")

    def _import_browser_profile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "USB / Diskten Profil Yükle",
            "",
            "JSON Dosyaları (*.json)"
        )
        if file_path and os.path.isfile(file_path):
            imported = self.profile_mgr.import_profile_from_file(file_path)
            if imported:
                self._switch_to_profile(imported["id"])
                QMessageBox.information(
                    self,
                    "İçe Aktarma Başarılı",
                    f"'{imported['name']}' profili başarıyla yüklendi ve aktif profil olarak ayarlandı!\n\n"
                    f"• {len(imported.get('apps', []))} Program\n"
                    f"• {len(imported.get('tweaks', []))} Windows İnce Ayarı\n"
                    f"• {len(imported.get('backups', []))} Yedekleme Öğesi"
                )
            else:
                QMessageBox.critical(self, "Hata", "Profil dosyası okunamadı veya biçim geçersiz!")

    def _save_profile(self):
        self._export_active_browser_profile()

    def _load_profile(self):
        self._import_browser_profile()

    # =========================================================================
    # INSTALLATION & DOWNLOAD FLOW
    # =========================================================================

    def _start_download_setups(self):
        selected_pkgs = [pkg for pkg in PACKAGES if self.app_cards[pkg["id"]].is_selected()]
        if not selected_pkgs:
            QMessageBox.warning(self, "Uyarı", "Lütfen setup dosyalarını indirmek için en az bir program seçin!")
            return

        default_dir = r"D:\Keystone_Setuplar" if os.path.exists("D:\\") else os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")), "Downloads", "Keystone_Setuplar"
        )
        directory = QFileDialog.getExistingDirectory(
            self, "Setup Dosyalarının Kaydedileceği Klasörü Seçin", default_dir
        )
        if not directory:
            return

        self.last_download_target_dir = directory
        self.worker_mode = "download"

        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Klasör Hatası", f"Hedef klasör oluşturulamadı:\n{e}")
            return

        self.terminal_console.show()
        self.btn_terminal.setText("Konsolu Gizle")
        self.terminal_console.clear()

        self.btn_action.setEnabled(False)
        if hasattr(self, "btn_download_setups"):
            self.btn_download_setups.setEnabled(False)
        self.btn_cancel.show()
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Setup Dosyaları İndiriliyor... [0/{len(selected_pkgs)}]")

        self.worker = InstallWorker(selected_pkgs, mode="download", download_dir=directory)
        self.worker.started_package.connect(self._on_pkg_started)
        self.worker.output_line.connect(self._on_worker_log)
        self.worker.progress_percent.connect(self._on_worker_progress)
        self.worker.finished_package.connect(self._on_pkg_finished)
        self.worker.finished_all.connect(self._on_all_finished)
        self.worker.start()

    def _start_installation(self):
        selected_pkgs = [pkg for pkg in PACKAGES if self.app_cards[pkg["id"]].is_selected()]
        if not selected_pkgs:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir paket seçin!")
            return

        self.worker_mode = "install"
        self.terminal_console.show()
        self.btn_terminal.setText("Konsolu Gizle")
        self.terminal_console.clear()

        self.btn_action.setEnabled(False)
        if hasattr(self, "btn_download_setups"):
            self.btn_download_setups.setEnabled(False)
        self.btn_cancel.show()
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Kuruluyor... [0/{len(selected_pkgs)}]")

        self.worker = InstallWorker(selected_pkgs, mode="install")
        self.worker.started_package.connect(self._on_pkg_started)
        self.worker.output_line.connect(self._on_worker_log)
        self.worker.progress_percent.connect(self._on_worker_progress)
        self.worker.finished_package.connect(self._on_pkg_finished)
        self.worker.finished_all.connect(self._on_all_finished)
        self.worker.start()

    def _cancel_installation(self):
        if self.worker:
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.btn_cancel.setText("Durduruluyor...")

    @pyqtSlot(dict, int, int)
    def _on_pkg_started(self, pkg: dict, idx: int, total: int):
        card = self.app_cards.get(pkg["id"])
        is_dl = getattr(self, "worker_mode", "install") == "download"
        if card:
            card.set_installing_status("[İndiriliyor...]" if is_dl else "[Yükleniyor...]")
        act_text = "indiriliyor" if is_dl else "yükleniyor"
        self.progress_bar.setFormat(f"{pkg['name']} {act_text}... [{idx}/{total}]")

    @pyqtSlot(str, str)
    def _on_worker_log(self, pkg_id: str, line: str):
        self.terminal_console.append(line)
        cursor = self.terminal_console.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.terminal_console.setTextCursor(cursor)

    @pyqtSlot(int, int)
    def _on_worker_progress(self, overall_pct: int, pkg_pct: int):
        self.progress_bar.setValue(overall_pct)

    @pyqtSlot(dict, bool, str)
    def _on_pkg_finished(self, pkg: dict, success: bool, msg: str):
        card = self.app_cards.get(pkg["id"])
        is_dl = getattr(self, "worker_mode", "install") == "download"
        if card:
            card.set_finished_status(success, msg)
            if success and not is_dl:
                card.set_installed_status(True)

    @pyqtSlot(int, int, list)
    def _on_all_finished(self, success_count: int, fail_count: int, failed_items: list):
        self.btn_action.setEnabled(True)
        if hasattr(self, "btn_download_setups"):
            self.btn_download_setups.setEnabled(True)
        self.btn_cancel.hide()
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setText("İptal Et")

        is_dl = getattr(self, "worker_mode", "install") == "download"

        if is_dl:
            target_dir = getattr(self, "last_download_target_dir", "")
            if target_dir:
                clean_yaml_manifests(target_dir)
            if fail_count == 0:
                self.progress_bar.setFormat("İndirme Tamamlandı! [%p%]")
                reply = QMessageBox.question(
                    self,
                    "Setup Dosyaları İndirildi",
                    f"Seçilen tüm programların ({success_count} adet) kurulum setup dosyaları başarıyla indirildi:\n\n"
                    f"'{target_dir}'\n\n"
                    "İndirilen kurulum klasörü şimdi açılsın mı?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes and target_dir and os.path.exists(target_dir):
                    os.startfile(target_dir)
            else:
                self.progress_bar.setFormat(f"Bitti: {success_count} İndirildi, {fail_count} Hata")
                fail_text = "\n• " + "\n• ".join(failed_items)
                reply = QMessageBox.question(
                    self,
                    "İndirme Özeti",
                    f"İndirme işlemi tamamlandı:\n"
                    f"Başarılı İndirilen: {success_count}\n"
                    f"Başarısız / Atlanan: {fail_count}\n\n"
                    f"Başarısız Olanlar:{fail_text}\n\n"
                    f"Hedef Klasör: {target_dir}\n\n"
                    "Klasör açılsın mı?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes and target_dir and os.path.exists(target_dir):
                    os.startfile(target_dir)
        else:
            if fail_count == 0:
                self.progress_bar.setFormat("Kurulum Tamamlandı! [%p%]")
                QMessageBox.information(
                    self,
                    "Kurulum Tamamlandı",
                    f"Seçilen tüm paketler ({success_count} adet) başarıyla kuruldu.\n\n"
                    "Sisteminiz kullanıma hazır!"
                )
            else:
                self.progress_bar.setFormat(f"Bitti: {success_count} Başarılı, {fail_count} Hata")
                fail_text = "\n• " + "\n• ".join(failed_items)
                QMessageBox.warning(
                    self,
                    "Kurulum Özeti",
                    f"Kurulum tamamlandı:\n"
                    f"Başarılı: {success_count}\n"
                    f"Başarısız / Atlanan: {fail_count}\n\n"
                    f"Başarısız Olanlar:{fail_text}\n\n"
                    f"Detaylar için konsol günlüğünü inceleyebilirsiniz."
                )

    # =========================================================================
    # BACKUP & RESTORE EXECUTION FLOW
    # =========================================================================

    def _start_backup_restore(self):
        target_dir = self.backup_dir_input.text().strip()
        if not target_dir:
            QMessageBox.warning(self, "Uyarı", "Lütfen geçerli bir yedekleme klasörü yolu girin!")
            return

        selected_items = [item for item in BACKUP_ITEMS if self.backup_cards[item["id"]].is_selected()]
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen işlem yapmak için en az bir ayar öğesi seçin!")
            return

        action_name = "Yedekleme" if self.backup_mode_operation == "backup" else "Geri Yükleme"
        prompt_msg = (
            f"Seçilen {len(selected_items)} adet ayar ve konfigürasyon öğesi şu klasöre yedeklenecektir:\n\n"
            f"'{target_dir}'\n\n"
            "İşlemi başlatmak istiyor musunuz?"
            if self.backup_mode_operation == "backup"
            else
            f"Seçilen {len(selected_items)} adet ayar ve konfigürasyon öğesi şu klasörden sisteme geri yüklenecektir:\n\n"
            f"'{target_dir}'\n\n"
            "İşlemi başlatmak istiyor musunuz?"
        )

        reply = QMessageBox.question(
            self,
            f"{action_name} Onayı",
            prompt_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Klasör Hatası", f"Hedef klasör oluşturulamadı:\n{e}")
            return

        self.terminal_console.show()
        self.btn_terminal.setText("Konsolu Gizle")
        self.terminal_console.clear()

        self.btn_action.setEnabled(False)
        self.btn_cancel.show()
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"{action_name} Başlatılıyor... [0/{len(selected_items)}]")

        self.worker = BackupWorker(selected_items, self.backup_mode_operation, target_dir)
        self.worker.started_item.connect(self._on_backup_worker_started)
        self.worker.output_line.connect(self._on_backup_worker_log)
        self.worker.progress_percent.connect(self._on_backup_worker_progress)
        self.worker.finished_item.connect(self._on_backup_worker_finished)
        self.worker.finished_all.connect(self._on_backup_all_finished)
        self.worker.start()

    @pyqtSlot(dict, int, int)
    def _on_backup_worker_started(self, item: dict, idx: int, total: int):
        act_title = "Yedekleniyor" if self.backup_mode_operation == "backup" else "Geri Yükleniyor"
        self.progress_bar.setFormat(f"{item['name']} {act_title.lower()}... [{idx}/{total}]")

    @pyqtSlot(str)
    def _on_backup_worker_log(self, line: str):
        self.terminal_console.append(line)
        cursor = self.terminal_console.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.terminal_console.setTextCursor(cursor)

    @pyqtSlot(int)
    def _on_backup_worker_progress(self, pct: int):
        self.progress_bar.setValue(pct)

    @pyqtSlot(dict, bool, str)
    def _on_backup_worker_finished(self, item: dict, success: bool, msg: str):
        card = self.backup_cards.get(item["id"])
        if card:
            action_label = "Yedeklendi" if self.backup_mode_operation == "backup" else "Geri Yüklendi"
            card.set_action_status(action_label if success else "Hata", success)

    @pyqtSlot(int, int, list)
    def _on_backup_all_finished(self, success_count: int, fail_count: int, failed_items: list):
        self.btn_action.setEnabled(True)
        self.btn_cancel.hide()
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setText("İptal Et")

        action_name = "Yedekleme" if self.backup_mode_operation == "backup" else "Geri Yükleme"
        if fail_count == 0:
            self.progress_bar.setFormat(f"{action_name} Tamamlandı! [%p%]")
            QMessageBox.information(
                self,
                f"{action_name} Tamamlandı",
                f"Tüm seçili öğeler ({success_count} adet) başarıyla işlendi!\n\n"
                f"Hedef Klasör: {self.backup_dir}"
            )
        else:
            self.progress_bar.setFormat(f"Bitti: {success_count} Başarılı, {fail_count} Hata")
            fail_text = "\n• " + "\n• ".join(failed_items)
            QMessageBox.warning(
                self,
                f"{action_name} Özeti",
                f"{action_name} işlemi tamamlandı:\n"
                f"Başarılı: {success_count}\n"
                f"Başarısız: {fail_count}\n\n"
                f"Hata Oluşanlar:{fail_text}\n\n"
                "Detaylar için konsol günlüğünü inceleyebilirsiniz."
            )
        self._refresh_backup_statuses()



    # =========================================================================
    # RESPONSIVE LAYOUT & WINDOW SIZING METHODS
    # =========================================================================

    def _toggle_maximize(self):
        """Toggle between window maximized and normal size."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _on_splitter_moved(self, pos: int, index: int):
        """Automatically switch between slim rail and drawer if user drags the splitter handle."""
        if index == 1:
            if pos < 90 and not getattr(self, "is_sidebar_collapsed", False):
                self._toggle_sidebar(force_collapse=True)
            elif pos >= 150 and getattr(self, "is_sidebar_collapsed", False):
                self._toggle_sidebar(force_expand=True)

    def _calculate_responsive_columns(self, target_card_width: int, min_cols: int, max_cols: int) -> int:
        """Calculate dynamic grid columns based on the current width of the right content pane."""
        sidebar_w = 50 if getattr(self, "is_sidebar_collapsed", False) else 220
        fallback_w = max(200, self.width() - sidebar_w - 40)
        if hasattr(self, "stack") and self.stack.width() > 300:
            avail_w = max(self.stack.width() - 36, fallback_w)
        else:
            avail_w = fallback_w
        cols = max(min_cols, min(max_cols, max(1, avail_w // target_card_width)))
        return cols

    def _relayout_all_grids(self):
        """Re-layout cards across all tabs strictly into single-column vertical downward lists."""
        needs_app = getattr(self, "_app_grid_cols", 1) != 1
        needs_tweak = getattr(self, "_tweak_grid_cols", 1) != 1
        needs_backup = getattr(self, "_backup_grid_cols", 1) != 1

        self._app_grid_cols = 1
        self._tweak_grid_cols = 1
        self._backup_grid_cols = 1

        if hasattr(self, "app_grid"):
            self._filter_app_cards()
        if hasattr(self, "tweaks_grid"):
            self._relayout_tweak_grid()
        if hasattr(self, "backup_grid"):
            self._relayout_backup_grid()

    def resizeEvent(self, event):
        """Handle dynamic window resizing smoothly without UI stutter or lag."""
        super().resizeEvent(event)
        self._update_responsive_bars()

        is_large = self.width() >= 1300
        if is_large != getattr(self, "_last_is_large", None):
            self._last_is_large = is_large
            for card in self.app_cards.values():
                if hasattr(card, "set_dynamic_scale"):
                    card.set_dynamic_scale(is_large)
            for card in self.tweak_cards.values():
                if hasattr(card, "set_dynamic_scale"):
                    card.set_dynamic_scale(is_large)
            for card in self.backup_cards.values():
                if hasattr(card, "set_dynamic_scale"):
                    card.set_dynamic_scale(is_large)

    def _update_responsive_bars(self):
        """Dynamically scales button dimensions, font sizes, padding, and search box widths
        based on the window width to ensure category and preset buttons never squash or overlap."""
        w = self.width()
        if w >= 1350:
            tier = "wide"
            fs, pv, ph, bh, sw = (12, 5, 12, 28, 240)
        elif w >= 1150:
            tier = "normal"
            fs, pv, ph, bh, sw = (11, 4, 8, 26, 190)
        elif w >= 950:
            tier = "compact"
            fs, pv, ph, bh, sw = (10, 3, 6, 24, 150)
        else:
            tier = "small"
            fs, pv, ph, bh, sw = (9, 2, 4, 22, 115)

        if getattr(self, "_current_bar_tier", None) != tier:
            self._current_bar_tier = tier
            bar_css = f"""
            .categoryTab {{
                padding: {pv}px {ph}px;
                font-size: {fs}px;
                min-height: {bh}px;
            }}
            .presetBtn {{
                padding: {pv}px {ph}px;
                font-size: {fs}px;
                min-height: {bh}px;
            }}
            #presetBar QLabel, #categoryBar QLabel {{
                font-size: {max(9, fs - 1)}px;
            }}
            """
            for bar in (getattr(self, "preset_bar_apps", None),
                        getattr(self, "cat_bar_apps", None),
                        getattr(self, "preset_bar_tweaks", None),
                        getattr(self, "control_bar_backup", None)):
                if bar:
                    bar.setStyleSheet(bar_css)

            if hasattr(self, "app_search_box") and self.app_search_box.width() != sw:
                self.app_search_box.setFixedWidth(sw)
            if hasattr(self, "tweak_search_box") and self.tweak_search_box.width() != sw:
                self.tweak_search_box.setFixedWidth(sw)

    def _relayout_tweak_grid(self):
        """Re-layout tweak cards respecting search filter across all categories."""
        filter_text = getattr(self, "tweak_search_filter", "").strip().lower()
        if not hasattr(self, "tweaks_grid") or not hasattr(self, "tweak_cards"):
            return

        while self.tweaks_grid.count():
            self.tweaks_grid.takeAt(0)

        visible_idx = 0
        for tweak in TWEAKS:
            card = self.tweak_cards.get(tweak["id"])
            if not card:
                continue

            cat = tweak.get("category", "")
            if filter_text:
                match_cat = True
            else:
                match_cat = (self.current_tweak_category == "all" or cat == self.current_tweak_category)

            if not filter_text:
                match_search = True
            else:
                match_search = (
                    filter_text in tweak["name"].lower() or
                    filter_text in tweak.get("short_desc", "").lower() or
                    filter_text in tweak["id"].lower()
                )

            card.setVisible(match_cat and match_search)
            if match_cat and match_search:
                self.tweaks_grid.addWidget(card, visible_idx, 0)
                self.tweaks_grid.setRowStretch(visible_idx, 0)
                visible_idx += 1

        self.tweaks_grid.setRowStretch(visible_idx, 1)

    def _relayout_backup_grid(self):
        """Re-layout backup items strictly in single column list."""
        if not hasattr(self, "backup_grid") or not hasattr(self, "backup_cards"):
            return

        while self.backup_grid.count():
            self.backup_grid.takeAt(0)

        for idx, item in enumerate(BACKUP_ITEMS):
            card = self.backup_cards.get(item["id"])
            if card:
                self.backup_grid.addWidget(card, idx, 0)
                self.backup_grid.setRowStretch(idx, 0)

        self.backup_grid.setRowStretch(len(BACKUP_ITEMS), 1)

    # =========================================================================
    # SETTINGS TAB & CONTROLS
    # =========================================================================

    def _build_settings_page(self) -> QWidget:
        """TAB 4: SETTINGS PAGE (Appearance / Day-Night Theme & Profile Management)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header_bar = QFrame()
        header_bar.setObjectName("categoryBar")
        hb_layout = QHBoxLayout(header_bar)
        hb_layout.setContentsMargins(20, 10, 20, 10)
        hb_layout.setSpacing(10)

        lbl_title = QLabel("Ayarlar")
        lbl_title.setProperty("class", "settingsHeaderTitle")
        hb_layout.addWidget(lbl_title)

        lbl_desc = QLabel("•  Görünüm modu (Gece/Gündüz) ve profil tercihleri")
        lbl_desc.setProperty("class", "settingsHeaderDesc")
        hb_layout.addWidget(lbl_desc)
        hb_layout.addStretch()
        layout.addWidget(header_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(24, 18, 24, 24)
        scroll_layout.setSpacing(16)

        # Theme Card
        card_theme = QFrame()
        card_theme.setProperty("class", "settingsCard")
        theme_layout = QVBoxLayout(card_theme)
        theme_layout.setContentsMargins(18, 16, 18, 16)
        theme_layout.setSpacing(14)

        t_header = QVBoxLayout()
        t_header.setSpacing(2)
        lbl_theme_title = QLabel("Görünüm & Renk Teması")
        lbl_theme_title.setProperty("class", "settingsSectionTitle")
        lbl_theme_desc = QLabel("Uygulamanın renk modunu gece (karanlık) veya gündüz (aydınlık) olarak değiştirin.")
        lbl_theme_desc.setProperty("class", "settingsSectionDesc")
        t_header.addWidget(lbl_theme_title)
        t_header.addWidget(lbl_theme_desc)
        theme_layout.addLayout(t_header)

        theme_seg = QFrame()
        theme_seg.setObjectName("themeSegmentContainer")
        seg_layout = QHBoxLayout(theme_seg)
        seg_layout.setContentsMargins(3, 3, 3, 3)
        seg_layout.setSpacing(4)

        self.btn_theme_dark = QPushButton("Karanlık Mod")
        self.btn_theme_dark.setProperty("class", "themeSegmentBtn")
        self.btn_theme_dark.setProperty("selected", "true" if self.current_theme == "dark" else "false")
        self.btn_theme_dark.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme_dark.clicked.connect(lambda: self._set_theme("dark"))
        seg_layout.addWidget(self.btn_theme_dark)

        self.btn_theme_light = QPushButton("Aydınlık Mod")
        self.btn_theme_light.setProperty("class", "themeSegmentBtn")
        self.btn_theme_light.setProperty("selected", "true" if self.current_theme == "light" else "false")
        self.btn_theme_light.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme_light.clicked.connect(lambda: self._set_theme("light"))
        seg_layout.addWidget(self.btn_theme_light)

        theme_layout.addWidget(theme_seg)
        scroll_layout.addWidget(card_theme)

        # Profile Card
        card_profile = QFrame()
        card_profile.setProperty("class", "settingsCard")
        prof_layout = QVBoxLayout(card_profile)
        prof_layout.setContentsMargins(18, 16, 18, 16)
        prof_layout.setSpacing(14)

        p_info = QVBoxLayout()
        p_info.setSpacing(2)
        lbl_prof_title = QLabel("Çalışma Profili Yönetimi")
        lbl_prof_title.setProperty("class", "settingsSectionTitle")
        lbl_prof_desc = QLabel("Farklı kurulum senaryoları için bağımsız profiller oluşturun ve seçimlerinizi ayrı ayrı saklayın.")
        lbl_prof_desc.setProperty("class", "settingsSectionDesc")
        p_info.addWidget(lbl_prof_title)
        p_info.addWidget(lbl_prof_desc)
        prof_layout.addLayout(p_info)

        prof_row = QHBoxLayout()
        prof_row.setSpacing(10)
        lbl_active_p = QLabel("Aktif Profil:")
        lbl_active_p.setStyleSheet("font-weight: 600; font-size: 13px;")
        prof_row.addWidget(lbl_active_p)

        self.combo_profiles = QComboBox()
        self.combo_profiles.setObjectName("settingsComboBox")
        self.combo_profiles.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_profile_combo()
        self.combo_profiles.currentIndexChanged.connect(self._on_settings_profile_changed)
        prof_row.addWidget(self.combo_profiles, stretch=1)

        btn_new_p = QPushButton("+ Yeni Profil")
        btn_new_p.setProperty("class", "settingsActionBtn")
        btn_new_p.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_p.setToolTip("Sıfırdan bağımsız yeni bir profil oluşturur")
        btn_new_p.clicked.connect(self._add_new_browser_profile)
        prof_row.addWidget(btn_new_p)

        btn_rename_p = QPushButton("Yeniden Adlandır")
        btn_rename_p.setProperty("class", "settingsActionBtn")
        btn_rename_p.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rename_p.setToolTip("Seçili profilin ismini değiştirir")
        btn_rename_p.clicked.connect(self._rename_active_browser_profile)
        prof_row.addWidget(btn_rename_p)

        btn_del_p = QPushButton("Profili Sil")
        btn_del_p.setProperty("class", "settingsDangerBtn")
        btn_del_p.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_p.setToolTip("Seçili profili kalıcı olarak siler")
        btn_del_p.clicked.connect(self._delete_active_browser_profile)
        prof_row.addWidget(btn_del_p)
        prof_layout.addLayout(prof_row)

        self.profile_stats_label = QLabel()
        self.profile_stats_label.setStyleSheet("color: #0A84FF; font-size: 12px; font-weight: 500; padding: 4px 0px;")
        self._update_settings_profile_stats()
        prof_layout.addWidget(self.profile_stats_label)
        scroll_layout.addWidget(card_profile)

        # System / Admin Elevation Card
        card_system = QFrame()
        card_system.setProperty("class", "settingsCard")
        sys_layout = QVBoxLayout(card_system)
        sys_layout.setContentsMargins(18, 16, 18, 16)
        sys_layout.setSpacing(14)

        sys_info = QVBoxLayout()
        sys_info.setSpacing(2)
        lbl_sys_title = QLabel("Yönetici Hakları (Admin Elevation)")
        lbl_sys_title.setProperty("class", "settingsSectionTitle")
        lbl_sys_desc = QLabel("Windows Regedit ayarlarının uygulanabilmesi ve yazılım kurulumları için gereklidir.")
        lbl_sys_desc.setProperty("class", "settingsSectionDesc")
        sys_info.addWidget(lbl_sys_title)
        sys_info.addWidget(lbl_sys_desc)
        sys_layout.addLayout(sys_info)

        if is_admin():
            lbl_adm = QLabel("Yönetici Yetkisi: Aktif")
            lbl_adm.setProperty("class", "pkgInstalledBadge")
            lbl_adm.setStyleSheet("font-size: 12px; padding: 6px 14px; border-radius: 8px;")
            sys_layout.addWidget(lbl_adm)
        else:
            btn_adm = QPushButton("Yönetici Olarak Yeniden Başlat")
            btn_adm.setProperty("class", "settingsActionBtn")
            btn_adm.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_adm.clicked.connect(self._elevate_admin)
            sys_layout.addWidget(btn_adm)
        scroll_layout.addWidget(card_system)

        # About Card
        card_about = QFrame()
        card_about.setProperty("class", "settingsCard")
        ab_layout = QVBoxLayout(card_about)
        ab_layout.setContentsMargins(18, 16, 18, 16)
        ab_layout.setSpacing(8)

        ab_title = QLabel("Keystone  •  Sürüm 2.0 (Portable)")
        ab_title.setStyleSheet("color: #8E8E93; font-size: 12px; font-weight: 500;")
        ab_layout.addWidget(ab_title)
        scroll_layout.addWidget(card_about)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return page

    def _set_theme(self, theme: str):
        """Set application theme ('dark' or 'light') directly."""
        self._apply_theme(theme)

    def _refresh_profile_combo(self):
        """Refresh profile selection combobox in the settings view."""
        if not hasattr(self, "combo_profiles"):
            return
        self.combo_profiles.blockSignals(True)
        self.combo_profiles.clear()
        for idx, p in enumerate(self.profile_mgr.get_all_profiles()):
            self.combo_profiles.addItem(p.get("name", "Profil"), p.get("id"))
            if p.get("id") == self.profile_mgr.active_profile_id:
                self.combo_profiles.setCurrentIndex(idx)
        self.combo_profiles.blockSignals(False)
        self._update_settings_profile_stats()

    def _on_settings_profile_changed(self, index: int):
        """Handle profile combobox changes in Settings tab."""
        if index < 0 or not hasattr(self, "combo_profiles"):
            return
        prof_id = self.combo_profiles.currentData()
        if prof_id and prof_id != self.profile_mgr.active_profile_id:
            self._switch_to_profile(prof_id)
            self._update_settings_profile_stats()

    def _update_settings_profile_stats(self):
        """Update live statistics label in Settings tab for the active profile."""
        if not hasattr(self, "profile_stats_label"):
            return
        active = self.profile_mgr.get_active_profile()
        if not active:
            self.profile_stats_label.setText("")
            return
        n_apps = len(active.get("apps", []))
        n_tweaks = len(active.get("tweaks", []))
        n_backup = len(active.get("backups", []))
        created = active.get("created_at", "")
        self.profile_stats_label.setText(
            f"Profil Durumu: {n_apps} Program Seçili  •  "
            f"{n_tweaks} Regedit Ayarı  •  "
            f"{n_backup} Yedekleme  •  Oluşturulma: {created}"
        )

    def _toggle_settings(self):
        """Toggle settings view: if already in settings, return to previous tab/window; otherwise enter settings."""
        if self.current_mode == "settings":
            prev = getattr(self, "previous_mode", "apps")
            if prev == "settings":
                prev = "apps"
            self._switch_main_mode(prev)
        else:
            self.previous_mode = self.current_mode
            self._switch_main_mode("settings")

    def _on_preset_combo_changed(self, index: int):
        """Handle preset dropdown selection."""
        if getattr(self, "_is_updating_preset_combo", False):
            return
        preset_key = self.preset_combo.currentData()
        if preset_key:
            self._apply_app_preset(preset_key)

    def _apply_current_preset_combo(self):
        """Apply currently selected preset in dropdown."""
        preset_key = self.preset_combo.currentData()
        if preset_key:
            self._apply_app_preset(preset_key)

    def _clear_terminal(self):
        """Clear text in embedded terminal console."""
        if hasattr(self, "terminal_console"):
            self.terminal_console.clear()

    def _clear_icon_cache_action(self):
        """Confirm and clear Windows Icon Cache, restarting explorer."""
        reply = QMessageBox.question(
            self,
            "İkon Önbelleğini Temizle",
            "Windows görev çubuğu ve simge önbelleği (IconCache.db) temizlenip Gezgin yeniden başlatılsın mı?\n\n"
            "Bu işlem bozuk veya beyaz görünen görev çubuğu simgelerini onarır.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from tweaks_manager import clear_icon_cache
            self._append_log("[SİSTEM] Windows simge önbelleği (IconCache.db) temizleniyor...")
            ok = clear_icon_cache()
            if ok:
                self._append_log("[BAŞARILI] İkon önbelleği sıfırlandı ve Explorer yeniden başlatıldı.")
            else:
                self._append_log("[UYARI] İkon önbelleği temizleme işlemi tamamlandı.")

    def _update_sidebar_icons(self, theme: str):
        """Updates all tab and sidebar icons to single unified monochrome color matching the active theme."""
        suffix = "_light.svg" if theme == "light" else ".svg"
        apps_icon = QIcon(resource_path(f"assets/icons/apps{suffix}"))
        tweaks_icon = QIcon(resource_path(f"assets/icons/tweaks{suffix}"))
        backup_icon = QIcon(resource_path(f"assets/icons/backup{suffix}"))
        settings_icon = QIcon(resource_path(f"assets/icons/settings{suffix}"))
        c_left_icon = QIcon(resource_path(f"assets/icons/chevron_left{suffix}"))
        c_right_icon = QIcon(resource_path(f"assets/icons/chevron_right{suffix}"))

        if hasattr(self, "tab_btn_apps"):
            self.tab_btn_apps.setIcon(apps_icon)
        if hasattr(self, "btn_rail_apps"):
            self.btn_rail_apps.setIcon(apps_icon)

        if hasattr(self, "tab_btn_tweaks"):
            self.tab_btn_tweaks.setIcon(tweaks_icon)
        if hasattr(self, "btn_rail_tweaks"):
            self.btn_rail_tweaks.setIcon(tweaks_icon)

        if hasattr(self, "tab_btn_backup"):
            self.tab_btn_backup.setIcon(backup_icon)
        if hasattr(self, "btn_rail_backup"):
            self.btn_rail_backup.setIcon(backup_icon)

        if hasattr(self, "btn_settings_header"):
            self.btn_settings_header.setIcon(settings_icon)

        if hasattr(self, "btn_drawer_collapse"):
            self.btn_drawer_collapse.setIcon(c_left_icon)
        if hasattr(self, "btn_rail_expand"):
            self.btn_rail_expand.setIcon(c_right_icon)
