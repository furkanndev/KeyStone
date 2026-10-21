import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtWidgets import QApplication

from styles import get_stylesheet, get_theme_accent
from data.packages import PACKAGES, CATEGORIES
from ui_card import PackageCard

def verify():
    print("1. Verifying stylesheets and assets...")
    dark_css = get_stylesheet("dark")
    light_css = get_stylesheet("light")
    assert "apple_switch_on_dark.png" in dark_css, "Missing apple_switch_on_dark.png in dark_css"
    assert "apple_switch_off_dark.png" in dark_css, "Missing apple_switch_off_dark.png in dark_css"
    assert "apple_switch_on_light.png" in light_css, "Missing apple_switch_on_light.png in light_css"
    assert "apple_switch_off_light.png" in light_css, "Missing apple_switch_off_light.png in light_css"
    print("   Stylesheet asset URLs validated.")

    print("2. Verifying hardware test packages...")
    cat_ids = [c["id"] for c in CATEGORIES]
    assert "hardware_test" in cat_ids, "hardware_test category not in CATEGORIES"
    print(f"   Category found: {[c for c in CATEGORIES if c['id'] == 'hardware_test'][0]}")

    hw_keys = [
        "msi_afterburner", "open_hardware_monitor", "libre_hardware_monitor",
        "cpuz", "gpuz", "hwmonitor", "crystaldiskinfo", "crystaldiskmark", "furmark"
    ]
    for k in hw_keys:
        pkg = next((p for p in PACKAGES if p["id"] == k), None)
        assert pkg is not None, f"Package {k} not found in PACKAGES"
        print(f"   Found: {pkg['id']} -> {pkg['name']} (Cat: {pkg['category']}, Fallback: {bool(pkg.get('fallback_url'))})")

    print("3. Verifying Qt widget creation and toggling...")
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    app.setStyleSheet(dark_css)
    pkg = next(p for p in PACKAGES if p["id"] == "msi_afterburner")
    card = PackageCard(pkg, theme="dark")
    assert card.checkbox.isChecked() is False
    card.checkbox.setChecked(True)
    assert card.property("checked") == "true"
    card.checkbox.setChecked(False)
    assert card.property("checked") == "false"
    print("   PackageCard widget instantiated and toggled successfully.")

    print("\nALL VERIFICATIONS PASSED!")

if __name__ == "__main__":
    verify()
