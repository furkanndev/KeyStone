import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.packages import PACKAGES
from collections import Counter

ids = [p['id'] for p in PACKAGES]
counts = Counter(ids)
duplicates = {k: v for k, v in counts.items() if v > 1}
print("Duplicate package IDs:", duplicates)
for i, p in enumerate(PACKAGES):
    if p['id'] in ['cpuz', 'gpuz', 'hwmonitor', 'crystaldiskinfo', 'crystaldiskmark', 'furmark']:
        print(f"{i:03d}: {p['id']} (category={p['category']})")
