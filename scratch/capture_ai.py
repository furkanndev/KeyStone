import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from ui_main import MainWindow

app = QApplication(sys.argv)
win = MainWindow()
win.resize(1260, 900)
win.show()

# 1. Main Apps view (95 packages)
win._switch_main_mode("apps")
app.processEvents()
win.grab().save("scratch/view_95_apps.png")

# 2. Filtered to "ai" category
win._switch_app_category("ai")
app.processEvents()
win.grab().save("scratch/view_ai_category.png")

print("Screenshots saved successfully.")
