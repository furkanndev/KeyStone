"""
Build Script for RetroFormat
Compiles the application into a single standalone portable executable using PyInstaller.
"""

import os
import sys
import subprocess

# Ensure UTF-8 output in Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def build():
    print("=" * 60)
    print("RETRO FORMAT SETUP - PYINSTALLER DERLEME SIHIRBAZI")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "assets", "icon.ico")
    main_script = os.path.join(base_dir, "main.py")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=RetroSetup",
        "--onefile",
        "--windowed",
        f"--icon={icon_path}",
        "--add-data=assets;assets",
        "--add-data=data;data",
        "--clean",
        main_script
    ]

    print("\n[+] PyInstaller komutu calistiriliyor:")
    print(" ".join(cmd))
    print()

    res = subprocess.run(cmd, cwd=base_dir)
    if res.returncode == 0:
        exe_path = os.path.join(base_dir, "dist", "RetroSetup.exe")
        print("\n" + "=" * 60)
        print("TEBRIKLER! Derleme basariyla tamamlandi.")
        print(f"Tasinabilir EXE Dosyasi: {exe_path}")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"Dosya Boyutu: {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print("\n[X] Hata: Derleme islemi basarisiz oldu!")


if __name__ == "__main__":
    build()
