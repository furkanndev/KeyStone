import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from ui_main import MainWindow
from styles import get_stylesheet

app = QApplication(sys.argv)
win = MainWindow()
win.resize(1260, 900)
win.show()

# 1. Dark Mode Tests
win._apply_theme("dark")
app.processEvents()

win._switch_main_mode("apps")
app.processEvents()
win.grab().save("scratch/dark_tab1_apps.png")

win._switch_main_mode("tweaks")
app.processEvents()
win.grab().save("scratch/dark_tab2_tweaks.png")

win._switch_main_mode("backup")
app.processEvents()
win.grab().save("scratch/dark_tab3_backup.png")

# 2. Toggle to Light Mode
win._toggle_theme()
app.processEvents()
assert win.current_theme == "light", f"Expected light theme, got {win.current_theme}"

win._switch_main_mode("apps")
app.processEvents()
win.grab().save("scratch/light_tab1_apps.png")

win._switch_main_mode("tweaks")
app.processEvents()
win.grab().save("scratch/light_tab2_tweaks.png")

win._switch_main_mode("backup")
app.processEvents()
win.grab().save("scratch/light_tab3_backup.png")

# 3. Toggle back to Dark Mode
win._toggle_theme()
app.processEvents()
assert win.current_theme == "dark", f"Expected dark theme, got {win.current_theme}"

print("All dark and light mode screenshots captured successfully!")
