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

# Tab 1: Apps
win._switch_main_mode("apps")
app.processEvents()
win.grab().save("scratch/startup_tab1_apps.png")

# Tab 2: Tweaks
win._switch_main_mode("tweaks")
app.processEvents()
win.grab().save("scratch/startup_tab2_tweaks.png")

# Tab 3: Backup
win._switch_main_mode("backup")
app.processEvents()
win.grab().save("scratch/startup_tab3_backup.png")

print("Startup screenshots saved to scratch/")
