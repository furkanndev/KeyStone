import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from styles import get_stylesheet
from ui_main import MainWindow

def capture_ui():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    window = MainWindow()
    window.resize(1100, 750)
    window.show()

    def do_capture():
        # 1. Dark Apps
        window._apply_theme("dark")
        if "hardware_test" in window.app_category_buttons:
            window.app_category_buttons["hardware_test"].click()
        
        preview_dark_apps = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch", "apple_dark_apps.png")
        window.grab().save(preview_dark_apps, "PNG")
        print(f"Captured {preview_dark_apps}")

        # 2. Dark Tweaks
        window._switch_main_mode("tweaks")
        preview_dark_tweaks = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch", "apple_dark_tweaks.png")
        window.grab().save(preview_dark_tweaks, "PNG")
        print(f"Captured {preview_dark_tweaks}")

        # 3. Light Apps
        window._switch_main_mode("apps")
        window._apply_theme("light")
        preview_light_apps = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch", "apple_light_apps.png")
        window.grab().save(preview_light_apps, "PNG")
        print(f"Captured {preview_light_apps}")

        # Revert to dark
        window._apply_theme("dark")
        QTimer.singleShot(200, app.quit)

    QTimer.singleShot(600, do_capture)
    app.exec()


if __name__ == "__main__":
    capture_ui()
