"""
Generates English preview screenshots for Keystone documentation.
Captures:
- assets/screenshots/preview_apps.png (Dark Mode)
- assets/screenshots/preview_tweaks.png (Dark Mode)
- assets/screenshots/preview_backup.png (Dark Mode)
- assets/screenshots/preview_settings.png (Dark Mode - Preferences & Profile Management)
- assets/screenshots/preview_console.png (Dark Mode - Live Console Output)
- assets/screenshots/preview_light.png (Light Mode)
"""

import sys
import os
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase

from utils import resource_path
from styles import get_stylesheet
from ui_main import MainWindow
from locales import set_language
from data.packages import PACKAGES
from data.tweaks import TWEAKS
from backup_manager import BACKUP_ITEMS


def capture_all():
    set_language("en")

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Fonts
    f1 = resource_path(os.path.join("assets", "fonts", "PressStart2P-Regular.ttf"))
    f2 = resource_path(os.path.join("assets", "fonts", "PixelifySans.ttf"))
    if os.path.exists(f1):
        QFontDatabase.addApplicationFont(f1)
    if os.path.exists(f2):
        QFontDatabase.addApplicationFont(f2)

    app.setStyleSheet(get_stylesheet("dark"))

    win = MainWindow()
    win.resize(1280, 820)
    # Ensure profile name is 'Admin' for public documentation
    active_prof = win.profile_mgr.get_active_profile()
    active_prof["name"] = "Admin"
    win._update_profile_switcher_button()
    win._refresh_profile_combo()
    win._update_settings_profile_stats()
    win.show()
    app.processEvents()
    time.sleep(1.0)
    app.processEvents()

    out_dir = os.path.join("assets", "screenshots")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Preview Apps (Dark)
    print("Capturing preview_apps.png...")
    win._set_theme("dark")
    win._switch_main_mode("apps")
    app.processEvents()
    time.sleep(0.5)
    if PACKAGES:
        win._update_app_hud(PACKAGES[0])
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    win.grab().save(os.path.join(out_dir, "preview_apps.png"), "PNG")

    # 2. Preview Tweaks (Dark)
    print("Capturing preview_tweaks.png...")
    win._switch_main_mode("tweaks")
    app.processEvents()
    time.sleep(0.3)
    if TWEAKS:
        win._update_tweak_hud(TWEAKS[0])
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    win.grab().save(os.path.join(out_dir, "preview_tweaks.png"), "PNG")

    # 3. Preview Backup (Dark)
    print("Capturing preview_backup.png...")
    win._switch_main_mode("backup")
    app.processEvents()
    time.sleep(0.3)
    if BACKUP_ITEMS:
        win._on_backup_hovered(BACKUP_ITEMS[0])
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    win.grab().save(os.path.join(out_dir, "preview_backup.png"), "PNG")

    # 4. Preview Settings (Dark)
    print("Capturing preview_settings.png...")
    win._switch_main_mode("settings")
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()
    win.grab().save(os.path.join(out_dir, "preview_settings.png"), "PNG")

    # 5. Preview Console (Dark with log drawer open)
    print("Capturing preview_console.png...")
    win._switch_main_mode("apps")
    app.processEvents()
    if PACKAGES:
        win._update_app_hud(PACKAGES[0])
    if not win.terminal_console.isVisible():
        win._toggle_terminal()
    win.terminal_console.clear()
    win._append_log("[INITIALIZE] Keystone Core Engine v1.0 initialized successfully.")
    win._append_log("[SYSTEM] Windows 11 Build 26100 (x64) detected with Administrative elevation.")
    win._append_log("[WORKSPACE] Active Profile: 'Admin' (73 packages & tweaks selected).")
    win._append_log("[WINGET] Package database synchronized. 147 official definitions available.")
    win._append_log("[REGISTRY] Real-time registry scanner evaluated 14 optimizations.")
    win._append_log("[READY] Standing by for batch installation and deployment operations.")
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()
    win.grab().save(os.path.join(out_dir, "preview_console.png"), "PNG")
    if win.terminal_console.isVisible():
        win._toggle_terminal()

    # 6. Preview Light (Light Mode Apps)
    print("Capturing preview_light.png...")
    win._set_theme("light")
    win._switch_main_mode("apps")
    app.processEvents()
    time.sleep(0.4)
    if PACKAGES:
        win._update_app_hud(PACKAGES[0])
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    win.grab().save(os.path.join(out_dir, "preview_light.png"), "PNG")

    # Revert to dark theme for user
    win._set_theme("dark")
    win.close()
    print("All 6 screenshots captured successfully!")


if __name__ == "__main__":
    capture_all()
