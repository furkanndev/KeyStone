import sys
import os
import winreg
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.tweaks import TWEAKS
from tweaks_manager import check_tweak

print("--- TWEAK STATUSES ---")
for t in TWEAKS:
    status = check_tweak(t)
    print(f"ID: {t['id']} | Name: {t['name'][:35]} | check_tweak: {status}")
