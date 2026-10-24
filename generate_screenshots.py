"""
Generates English preview screenshots for Keystone documentation.
Captures:
- assets/screenshots/preview_apps.png (Dark Mode)
- assets/screenshots/preview_tweaks.png (Dark Mode)
- assets/screenshots/preview_backup.png (Dark Mode)
- assets/screenshots/preview_light.png (Light Mode)
"""

import sys
import os
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontDatabase, QIcon

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
    win.show()
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()

    out_dir = os.path.join("assets", "screenshots")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Preview Apps (Dark)
    print("Capturing preview_apps.png...")
    win._set_theme("dark")
    win._switch_main_mode("apps")
    app.processEvents()
    time.sleep(1.0)
    app.processEvents()
    if PACKAGES:
        win._update_app_hud(PACKAGES[0])
    app.processEvents()
    time.sleep(0.2)
    app.processEvents()
    pix_apps = win.grab()
    pix_apps.save(os.path.join(out_dir, "preview_apps.png"), "PNG")

    # 2. Preview Tweaks (Dark)
    print("Capturing preview_tweaks.png...")
    win._switch_main_mode("tweaks")
    if TWEAKS:
        win._update_tweak_hud(TWEAKS[0])
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()
    pix_tweaks = win.grab()
    pix_tweaks.save(os.path.join(out_dir, "preview_tweaks.png"), "PNG")

    # 3. Preview Backup (Dark)
    print("Capturing preview_backup.png...")
    win._switch_main_mode("backup")
    if BACKUP_ITEMS:
        win._on_backup_hovered(BACKUP_ITEMS[0])
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()
    pix_backup = win.grab()
    pix_backup.save(os.path.join(out_dir, "preview_backup.png"), "PNG")

    # 4. Preview Light (Light Mode Apps)
    print("Capturing preview_light.png...")
    win._set_theme("light")
    win._switch_main_mode("apps")
    if PACKAGES:
        win._update_app_hud(PACKAGES[0])
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()
    pix_light = win.grab()
    pix_light.save(os.path.join(out_dir, "preview_light.png"), "PNG")

    # Revert to dark theme for user
    win._set_theme("dark")
    win.close()
    print("All screenshots captured successfully!")


if __name__ == "__main__":
    capture_all()
