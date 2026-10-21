"""
RetroFormat - 8-Bit Post-Format Setup Wizard
Entry Point
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QIcon
from PyQt6.QtCore import Qt

from styles import get_stylesheet
from ui_main import MainWindow
from utils import resource_path


def setup_exception_handling():
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        import traceback
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"[FATAL ERROR] {err_msg}", file=sys.stderr)
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "RetroFormat - Hata",
                f"Beklenmeyen bir hata oluştu:\n\n{exc_value}\n\nProgram çalışmaya devam edebilir veya yeniden başlatabilirsiniz."
            )
        except Exception:
            pass

    sys.excepthook = handle_exception


def main():
    setup_exception_handling()
    app = QApplication(sys.argv)
    app.setApplicationName("RetroFormat")
    app.setOrganizationName("RetroSoft")

    # Load custom pixel fonts
    f1 = resource_path(os.path.join("assets", "fonts", "PressStart2P-Regular.ttf"))
    f2 = resource_path(os.path.join("assets", "fonts", "PixelifySans.ttf"))
    icon_path = resource_path(os.path.join("assets", "icon.ico"))

    if os.path.exists(f1):
        QFontDatabase.addApplicationFont(f1)
    if os.path.exists(f2):
        QFontDatabase.addApplicationFont(f2)

    # Set Application Icon
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply Pixel Art Stylesheet (loaded with saved theme preference)
    from profile_manager import BrowserProfileManager
    initial_theme = BrowserProfileManager().get_theme()
    app.setStyleSheet(get_stylesheet(initial_theme))

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
