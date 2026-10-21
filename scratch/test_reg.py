import winreg
import os
import sys

print("Checking registry permissions...")
try:
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion")
    print("HKCU read ok!")
    winreg.CloseKey(k)
except Exception as e:
    print("HKCU error:", e)

try:
    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion")
    print("HKLM read ok!")
    winreg.CloseKey(k)
except Exception as e:
    print("HKLM error:", e)
