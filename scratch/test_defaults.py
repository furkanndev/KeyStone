import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set offscreen platform for headless Qt testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from data.packages import PACKAGES
from data.tweaks import TWEAKS
from backup_manager import BACKUP_ITEMS

print("--- Testing Data Defaults ---")
true_pkg = [p["name"] for p in PACKAGES if p.get("default_checked") is True]
print(f"Packages with default_checked=True: {len(true_pkg)} {true_pkg}")
assert len(true_pkg) == 0, f"Found packages with default_checked=True: {true_pkg}"

true_tweak = [t["name"] for t in TWEAKS if t.get("default_checked") is True]
print(f"Tweaks with default_checked=True: {len(true_tweak)} {true_tweak}")
assert len(true_tweak) == 0, f"Found tweaks with default_checked=True: {true_tweak}"

print("\n--- Testing MainWindow UI Initialization ---")
app = QApplication(sys.argv)
from ui_main import MainWindow

win = MainWindow()
win.show()

# Initial mode is 'apps'
selected_apps = sum(1 for c in win.app_cards.values() if c.is_selected())
total_apps = len(win.app_cards)
print(f"Apps selected on startup: {selected_apps} / {total_apps}")
print(f"Apps counter label: '{win.counter_lbl.text()}'")
assert selected_apps == 0, f"Expected 0 selected apps, got {selected_apps}"
assert win.counter_lbl.text() == f"Seçilen: 0 / {total_apps} Program"
assert total_apps == 96, f"Expected 96 packages, got {total_apps}"
assert not win.btn_download_setups.isEnabled(), "Download setups button should be disabled when 0 selected"
assert win.btn_download_setups.isVisible(), "Download setups button should be visible on apps tab"

# Tweaks tab
selected_tweaks = sum(1 for c in win.tweak_cards.values() if c.is_selected())
total_tweaks = len(win.tweak_cards)
print(f"Tweaks selected on startup: {selected_tweaks} / {total_tweaks}")
assert selected_tweaks == 0, f"Expected 0 selected tweaks, got {selected_tweaks}"

win._switch_main_mode("tweaks")
print(f"Tweaks counter label: '{win.counter_lbl.text()}'")
assert win.counter_lbl.text() == f"Seçilen: 0 / {total_tweaks} Ayar"
assert win.btn_download_setups.isHidden(), "Download setups button should be hidden on tweaks tab"

# Backup tab
selected_backup = sum(1 for c in win.backup_cards.values() if c.is_selected())
total_backup = len(win.backup_cards)
print(f"Backup items selected on startup: {selected_backup} / {total_backup}")
assert selected_backup == 0, f"Expected 0 selected backup items, got {selected_backup}"

win._switch_main_mode("backup")
print(f"Backup counter label: '{win.counter_lbl.text()}'")
assert win.counter_lbl.text() == f"Seçilen: 0 / {total_backup} Ayar Öğesi"
assert win.btn_download_setups.isHidden(), "Download setups button should be hidden on backup tab"

print("\n--- Testing Presets and Select/Clear Actions ---")
# Apps tab presets
win._switch_main_mode("apps")
assert win.btn_download_setups.isVisible(), "Download setups button should be visible when returning to apps tab"
win._apply_app_preset("essential")
essential_count = sum(1 for c in win.app_cards.values() if c.is_selected())
print(f"Apps selected after 'essential' preset: {essential_count}")
assert essential_count > 0, "Essential preset should select packages"
assert win.btn_download_setups.isEnabled(), "Download setups button should be enabled when packages selected"

win._clear_all_apps()
assert not win.btn_download_setups.isEnabled(), "Download setups button should be disabled after clearing"
win._apply_app_preset("ai")
ai_count = sum(1 for c in win.app_cards.values() if c.is_selected())
print(f"Apps selected after 'ai' preset: {ai_count}")
assert ai_count == 10, f"Expected 10 AI packages, got {ai_count}"

# Test category filter for AI
win._switch_app_category("ai")
visible_ai = sum(1 for c in win.app_cards.values() if not c.isHidden())
print(f"Visible cards under 'ai' category: {visible_ai}")
assert visible_ai == 10, f"Expected 10 visible AI cards, got {visible_ai}"
win._switch_app_category("all")

win._toggle_select_apps() # Should select all
all_apps_count = sum(1 for c in win.app_cards.values() if c.is_selected())
print(f"Apps selected after 'Tümünü Seç': {all_apps_count} / {total_apps}")
assert all_apps_count == total_apps

win._toggle_select_apps() # Should clear all
cleared_apps_count = sum(1 for c in win.app_cards.values() if c.is_selected())
print(f"Apps selected after 'Temizle': {cleared_apps_count}")
assert cleared_apps_count == 0

# Tweaks tab presets
win._switch_main_mode("tweaks")
win._select_recommended_tweaks()
rec_tweaks_count = sum(1 for c in win.tweak_cards.values() if c.is_selected())
print(f"Tweaks selected after 'Önerilen Ayarları Seç': {rec_tweaks_count}")
assert rec_tweaks_count > 0, "Recommended tweaks should select tweaks"

win._clear_all_tweaks()
assert sum(1 for c in win.tweak_cards.values() if c.is_selected()) == 0

win._toggle_select_tweaks() # Should select all
all_tweaks_count = sum(1 for c in win.tweak_cards.values() if c.is_selected())
print(f"Tweaks selected after 'Tümünü Seç': {all_tweaks_count} / {total_tweaks}")
assert all_tweaks_count == total_tweaks

win._toggle_select_tweaks() # Should clear all
cleared_tweaks_count = sum(1 for c in win.tweak_cards.values() if c.is_selected())
print(f"Tweaks selected after 'Temizle': {cleared_tweaks_count}")
assert cleared_tweaks_count == 0

# Backup tab actions
win._switch_main_mode("backup")
win._toggle_select_backup() # Should select all
all_backup_count = sum(1 for c in win.backup_cards.values() if c.is_selected())
print(f"Backup selected after 'Tümünü Seç': {all_backup_count} / {total_backup}")
assert all_backup_count == total_backup

win._toggle_select_backup() # Should clear all
cleared_backup_count = sum(1 for c in win.backup_cards.values() if c.is_selected())
print(f"Backup selected after 'Temizle': {cleared_backup_count}")
assert cleared_backup_count == 0

# Test mode switching back and forth in backup tab (Backup vs Restore)
win._set_backup_operation("restore")
assert sum(1 for c in win.backup_cards.values() if c.is_selected()) == 0, "Restore switch should not select items"
win._set_backup_operation("backup")
assert sum(1 for c in win.backup_cards.values() if c.is_selected()) == 0, "Backup switch should not select items"

print("\nALL TESTS PASSED SUCCESSFULLY! No options selected on startup.")
