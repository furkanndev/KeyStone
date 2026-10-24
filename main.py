"""
Keystone - Post-Format Setup Wizard
Entry Point
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QIcon
from PyQt6.QtCore import Qt, QSize

from styles import get_stylesheet
from ui_main import MainWindow
from utils import resource_path


def ensure_admin():
    """Ensure process runs with Administrator privileges on Windows.
    If not elevated, re-launches with elevation via ShellExecuteW and terminates current process.
    Uses pythonw.exe if running from source to avoid any cmd window."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
    except Exception:
        return

    try:
        working_dir = os.path.abspath(os.getcwd())
        if getattr(sys, "frozen", False):
            # Running as compiled standalone executable
            exe = sys.executable
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, working_dir, 1)
        else:
            # Running from source: use pythonw.exe if available so no cmd prompt appears
            py_exe = sys.executable
            if py_exe.lower().endswith("python.exe"):
                pyw = os.path.join(os.path.dirname(py_exe), "pythonw.exe")
                if os.path.exists(pyw):
                    py_exe = pyw
            script = os.path.abspath(sys.argv[0])
            params = f'"{script}" ' + " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", py_exe, params, working_dir, 1)

        if ret > 32:
            sys.exit(0)
    except Exception:
        pass


def set_native_taskbar_icon(hwnd_val: int, icon_file: str):
    """Directly sends WM_SETICON and updates window class icons (HICON/HICONSM)
    on the Win32 window handle to guarantee taskbar appearance and prevent the white placeholder."""
    if sys.platform != "win32" or not os.path.exists(icon_file):
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        GCLP_HICON = -14
        GCLP_HICONSM = -34

        cx_sm = user32.GetSystemMetrics(49) or 16  # SM_CXSMICON
        cy_sm = user32.GetSystemMetrics(50) or 16  # SM_CYSMICON
        cx_lg = user32.GetSystemMetrics(11) or 32  # SM_CXICON
        cy_lg = user32.GetSystemMetrics(12) or 32  # SM_CYICON

        abs_icon = os.path.abspath(icon_file)
        user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.SendMessageW.restype = wintypes.LPARAM

        h_small = user32.LoadImageW(None, abs_icon, IMAGE_ICON, cx_sm, cy_sm, LR_LOADFROMFILE)
        h_big = user32.LoadImageW(None, abs_icon, IMAGE_ICON, cx_lg, cy_lg, LR_LOADFROMFILE)

        if h_small:
            user32.SendMessageW(hwnd_val, WM_SETICON, ICON_SMALL, h_small)
        if h_big:
            user32.SendMessageW(hwnd_val, WM_SETICON, ICON_BIG, h_big)

        # Set window class icon (fallback used by Explorer taskbar query)
        try:
            SetClassLongPtr = user32.SetClassLongPtrW
        except AttributeError:
            SetClassLongPtr = user32.SetClassLongW
        SetClassLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        SetClassLongPtr.restype = ctypes.c_void_p

        if h_big:
            SetClassLongPtr(hwnd_val, GCLP_HICON, h_big)
        if h_small:
            SetClassLongPtr(hwnd_val, GCLP_HICONSM, h_small)
    except Exception:
        pass


def build_multidpi_icon(icon_file: str) -> QIcon:
    """Build a multi-resolution QIcon containing all standard Windows DPI icon sizes."""
    icon = QIcon()
    if os.path.exists(icon_file):
        for s in (16, 20, 24, 32, 40, 48, 64, 96, 128, 256):
            icon.addFile(icon_file, QSize(s, s))
    return icon


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
                "Keystone - Hata",
                f"Beklenmeyen bir hata olustu:\n\n{exc_value}\n\nProgram calismaya devam edebilir veya yeniden baslatabilirsiniz."
            )
        except Exception:
            pass

    sys.excepthook = handle_exception


def main():
    # Guarantee Administrator Privileges on startup
    ensure_admin()

    setup_exception_handling()

    # Reason 1: Fix Windows taskbar icon by explicitly setting Application User Model ID
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "keystone.postformat.setup.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Keystone")
    app.setOrganizationName("Keystone")

    # Load custom pixel fonts & icon path
    f1 = resource_path(os.path.join("assets", "fonts", "PressStart2P-Regular.ttf"))
    f2 = resource_path(os.path.join("assets", "fonts", "PixelifySans.ttf"))
    icon_path = resource_path(os.path.join("assets", "icon.ico"))

    if os.path.exists(f1):
        QFontDatabase.addApplicationFont(f1)
    if os.path.exists(f2):
        QFontDatabase.addApplicationFont(f2)

    # Multi-DPI App Icon setup across all resolutions
    app_icon = build_multidpi_icon(icon_path)
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Apply Pixel Art Stylesheet (loaded with saved theme preference)
    from profile_manager import BrowserProfileManager
    initial_theme = BrowserProfileManager().get_theme()
    app.setStyleSheet(get_stylesheet(initial_theme))

    window = MainWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

    # CRITICAL: Native Win32 WM_SETICON & Class Icon binding directly on window HWND
    # Calling window.winId() creates the native Win32 HWND handle immediately.
    # Setting WM_SETICON and Class Icon BEFORE window.show() ensures Windows Explorer's
    # taskbar manager receives the icon on window creation, eliminating the default
    # white blank document placeholder!
    if os.path.exists(icon_path):
        set_native_taskbar_icon(int(window.winId()), icon_path)

    window.show()

    # Inform Explorer shell to refresh any cached icons
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except Exception:
            pass

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
