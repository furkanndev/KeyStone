import os
import sys
import winreg
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.tweaks import TWEAKS
from tweaks_manager import check_tweak, apply_tweak

print("Testing each tweak definition...")
for t in TWEAKS:
    tid = t["id"]
    name = t["name"]
    rtype = t["reg_type"]
    safe_name = name.encode('ascii', 'replace').decode('ascii')
    print(f"[{tid}] {safe_name} (type: {rtype})")
    curr_active = check_tweak(t)
    print(f"  Current active status: {curr_active}")
