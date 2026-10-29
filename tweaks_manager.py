"""
Windows Registry Tweaks Manager
Executes and queries registry settings and system tweaks.
"""

import os
import sys
import subprocess
import winreg
from installer import get_no_window_kwargs, get_winget_path


FOLDER_GUIDS = [
    "{0DB7E03F-FC29-4DC6-9020-FF41B59E513A}",  # 3D Objects
    "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",  # Desktop
    "{f42ee2d3-909f-4907-8871-4c22fc0bf756}",  # Documents
    "{7d83ee9b-2244-4e70-b1f5-5393042af1e4}",  # Downloads
    "{a0c69a99-21c8-4671-8703-7934162fcf1d}",  # Music
    "{0ddd015d-b06c-45d5-8c4c-f59713854639}",  # Pictures
    "{35286a68-3c57-41a1-bbb1-0eae73d76c95}",  # Videos
]


def check_tweak(tweak: dict) -> bool:
    """Check if a registry tweak is currently enabled in Windows."""
    reg_type = tweak.get("reg_type")
    try:
        if reg_type == "hkcu_clsid":
            # For Windows 11 Classic Context Menu
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                tweak["reg_key"],
                0,
                winreg.KEY_READ
            )
            winreg.CloseKey(key)
            return True

        elif reg_type == "remove_folders_64":
            root = winreg.HKEY_LOCAL_MACHINE
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions\{f42ee2d3-909f-4907-8871-4c22fc0bf756}\PropertyBag"
            key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "ThisPCPolicy")
            winreg.CloseKey(key)
            return str(val).lower() == "hide"

        elif reg_type == "remove_gallery":
            root = winreg.HKEY_LOCAL_MACHINE
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\NonEnum"
            key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "{e88865ea-0e1c-4e20-9aa6-edcd0212c87c}")
            winreg.CloseKey(key)
            return int(val) == 1

        elif reg_type == "photo_viewer":
            root = winreg.HKEY_LOCAL_MACHINE
            key_path = r"SOFTWARE\Microsoft\Windows Photo Viewer\Capabilities\FileAssociations"
            key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, ".jpg")
            winreg.CloseKey(key)
            return "PhotoViewer" in str(val)

        elif reg_type == "hkcu":
            root = winreg.HKEY_CURRENT_USER
            key = winreg.OpenKey(root, tweak["reg_key"], 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, tweak["reg_value_name"])
            winreg.CloseKey(key)
            return str(val) == str(tweak["reg_value_data"])

        elif reg_type == "hklm":
            root = winreg.HKEY_LOCAL_MACHINE
            key = winreg.OpenKey(root, tweak["reg_key"], 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, tweak["reg_value_name"])
            winreg.CloseKey(key)
            return str(val) == str(tweak["reg_value_data"])

        elif reg_type == "cmd":
            if tweak["id"] == "disable_hibernation":
                return not os.path.exists(r"C:\hiberfil.sys")

        elif reg_type == "disable_location" or tweak.get("id") == "disable_location":
            # Check Sensor Overrides (Windows 10/11 master switch)
            try:
                root = winreg.HKEY_LOCAL_MACHINE
                k = winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}", 0, winreg.KEY_READ)
                val, _ = winreg.QueryValueEx(k, "SensorPermissionState")
                winreg.CloseKey(k)
                if int(val) == 0:
                    return True
            except Exception:
                pass

            # Check Location Policies
            try:
                root = winreg.HKEY_LOCAL_MACHINE
                k = winreg.OpenKey(root, r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", 0, winreg.KEY_READ)
                val, _ = winreg.QueryValueEx(k, "DisableLocation")
                winreg.CloseKey(k)
                if int(val) == 1:
                    return True
            except Exception:
                pass

            # Check CapabilityAccessManager ConsentStore
            try:
                root = winreg.HKEY_LOCAL_MACHINE
                k = winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location", 0, winreg.KEY_READ)
                val, _ = winreg.QueryValueEx(k, "Value")
                winreg.CloseKey(k)
                if str(val).lower() == "deny":
                    return True
            except Exception:
                pass

            return False
    except Exception:
        return False
    return False


def apply_tweak(tweak: dict) -> tuple[bool, str]:
    """Apply a tweak to the Windows registry or system."""
    reg_type = tweak.get("reg_type")
    try:
        if reg_type == "hkcu_clsid":
            # Create key for classic context menu
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, tweak["reg_key"])
            winreg.SetValueEx(key, tweak["reg_value_name"], 0, winreg.REG_SZ, tweak["reg_value_data"])
            winreg.CloseKey(key)
            return True, "Kayıt defteri anahtarı başarıyla oluşturuldu."

        elif reg_type == "remove_folders_64":
            root = winreg.HKEY_LOCAL_MACHINE
            nodes = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions",
                r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions"
            ]
            for node in nodes:
                for guid in FOLDER_GUIDS:
                    sub_path = f"{node}\\{guid}\\PropertyBag"
                    try:
                        k = winreg.CreateKey(root, sub_path)
                        winreg.SetValueEx(k, "ThisPCPolicy", 0, winreg.REG_SZ, "Hide")
                        winreg.CloseKey(k)
                    except Exception:
                        pass
            return True, "Bu Bilgisayar kullanıcı klasörleri gizlendi (64-Bit)."

        elif reg_type == "remove_gallery":
            gallery_guid = "{e88865ea-0e1c-4e20-9aa6-edcd0212c87c}"
            k1 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\NonEnum")
            winreg.SetValueEx(k1, gallery_guid, 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k1)

            k2 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace\{gallery_guid}")
            winreg.SetValueEx(k2, "HiddenByDefault", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k2)

            k3 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\CLSID\{gallery_guid}")
            winreg.SetValueEx(k3, "System.IsPinnedToNameSpaceTree", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(k3)

            return True, "Galeri simgesi gezinti panelinden kaldırıldı."

        elif reg_type == "photo_viewer":
            assoc_path = r"SOFTWARE\Microsoft\Windows Photo Viewer\Capabilities\FileAssociations"
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, assoc_path)
            for ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".ico", ".tif", ".tiff"]:
                winreg.SetValueEx(key, ext, 0, winreg.REG_SZ, "PhotoViewer.FileAssoc.Tiff")
            winreg.CloseKey(key)

            app_reg = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\RegisteredApplications")
            winreg.SetValueEx(app_reg, "Windows Photo Viewer", 0, winreg.REG_SZ, r"SOFTWARE\Microsoft\Windows Photo Viewer\Capabilities")
            winreg.CloseKey(app_reg)

            return True, "Klasik Fotoğraf Görüntüleyicisi başarıyla aktif edildi."

        elif reg_type == "hkcu":
            root = winreg.HKEY_CURRENT_USER
            key = winreg.CreateKey(root, tweak["reg_key"])
            val_type = winreg.REG_DWORD if tweak["reg_value_type"] == "DWORD" else winreg.REG_SZ
            winreg.SetValueEx(key, tweak["reg_value_name"], 0, val_type, tweak["reg_value_data"])
            winreg.CloseKey(key)
            return True, "Ayar uygulandı."

        elif reg_type == "hklm":
            root = winreg.HKEY_LOCAL_MACHINE
            key = winreg.CreateKey(root, tweak["reg_key"])
            val_type = winreg.REG_DWORD if tweak["reg_value_type"] == "DWORD" else winreg.REG_SZ
            winreg.SetValueEx(key, tweak["reg_value_name"], 0, val_type, tweak["reg_value_data"])
            winreg.CloseKey(key)
            return True, "Sistem anahtarı uygulandı."

        elif reg_type == "disable_location" or tweak.get("id") == "disable_location":
            # 1. Disable Sensor Overrides (Windows Settings toggle)
            k1 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}")
            winreg.SetValueEx(k1, "SensorPermissionState", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(k1)

            # 2. Set Location & Sensors Group Policies
            k2 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors")
            winreg.SetValueEx(k2, "DisableLocation", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k2, "DisableLocationScripting", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k2, "DisableSensors", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k2, "DisableWindowsLocationProvider", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k2)

            # 3. Deny App Consent Store (HKLM and HKCU)
            try:
                k3 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location")
                winreg.SetValueEx(k3, "Value", 0, winreg.REG_SZ, "Deny")
                winreg.CloseKey(k3)
            except Exception:
                pass

            try:
                k4 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location")
                winreg.SetValueEx(k4, "Value", 0, winreg.REG_SZ, "Deny")
                winreg.CloseKey(k4)
            except Exception:
                pass

            # 4. Disable Geolocation Service (lfsvc)
            try:
                k5 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\lfsvc")
                winreg.SetValueEx(k5, "Start", 0, winreg.REG_DWORD, 4)
                winreg.CloseKey(k5)
            except Exception:
                pass

            try:
                subprocess.run(["sc", "stop", "lfsvc"], capture_output=True, **get_no_window_kwargs())
            except Exception:
                pass

            return True, "Windows konum ve lokasyon servisleri başarıyla kapatıldı."

        elif reg_type == "clear_icon_cache" or tweak.get("id") == "clear_icon_cache":
            ok = clear_icon_cache()
            if ok:
                return True, "İkon önbelleği (IconCache.db) temizlendi ve Gezgin yeniden başlatıldı."
            return False, "İkon önbelleği temizlenirken bir hata oluştu."

        elif reg_type == "cmd":
            cmd = tweak.get("command")
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, **get_no_window_kwargs())
            if res.returncode == 0:
                return True, "Komut başarıyla çalıştırıldı."
            return False, f"Hata: {res.stderr.strip() or 'Başarısız'}"

    except PermissionError:
        return False, "Yönetici izni gerekiyor (Uygulamayı Yönetici Olarak Başlatın)."
    except Exception as e:
        return False, f"Hata: {e}"

    return False, "Bilinmeyen ayar türü"


def _delete_key_recursive(root_key, subkey_path: str):
    """Recursively delete a registry key and all its subkeys."""
    try:
        key = winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    except PermissionError:
        try:
            key = winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_READ)
        except Exception:
            return
    except Exception:
        return

    while True:
        try:
            child_name = winreg.EnumKey(key, 0)
            _delete_key_recursive(root_key, f"{subkey_path}\\{child_name}")
        except OSError:
            break

    try:
        winreg.CloseKey(key)
    except Exception:
        pass

    try:
        winreg.DeleteKey(root_key, subkey_path)
    except Exception:
        pass


def _delete_val_safe(root_key, subkey_path: str, value_name: str) -> bool:
    """Safely delete a registry value without raising exceptions."""
    try:
        key = winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, value_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False


def revert_tweak(tweak: dict) -> tuple[bool, str]:
    """Revert/uninstall a tweak back to Windows original defaults."""
    tid = tweak.get("id")
    reg_type = tweak.get("reg_type")

    try:
        if tid == "classic_context_menu" or reg_type == "hkcu_clsid":
            clsid_path = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"
            _delete_key_recursive(winreg.HKEY_CURRENT_USER, clsid_path)
            return True, "Klasik sağ tık menüsü kaldırıldı, Windows 11 varsayılan menüsü geri getirildi."

        elif tid == "long_paths":
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, tweak["reg_key"])
            winreg.SetValueEx(key, "LongPathsEnabled", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            return True, "260 karakter dosya yolu sınırı varsayılana döndürüldü (Sınır aktif)."

        elif tid == "remove_user_folders" or reg_type == "remove_folders_64":
            root = winreg.HKEY_LOCAL_MACHINE
            nodes = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions",
                r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions"
            ]
            for node in nodes:
                for guid in FOLDER_GUIDS:
                    sub_path = f"{node}\\{guid}\\PropertyBag"
                    try:
                        k = winreg.CreateKey(root, sub_path)
                        winreg.SetValueEx(k, "ThisPCPolicy", 0, winreg.REG_SZ, "Show")
                        winreg.CloseKey(k)
                    except Exception:
                        pass
            return True, "Bu Bilgisayar kullanıcı klasörleri geri getirildi (Varsayılan)."

        elif tid == "remove_gallery" or reg_type == "remove_gallery":
            gallery_guid = "{e88865ea-0e1c-4e20-9aa6-edcd0212c87c}"
            _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\NonEnum", gallery_guid)
            _delete_key_recursive(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace\{gallery_guid}")
            _delete_key_recursive(winreg.HKEY_CURRENT_USER, rf"Software\Classes\CLSID\{gallery_guid}")
            return True, "Dosya Gezgini Galeri simgesi geri getirildi."

        elif tid == "disable_bing_search":
            _delete_val_safe(winreg.HKEY_CURRENT_USER, tweak["reg_key"], tweak["reg_value_name"])
            return True, "Başlat menüsü web araması varsayılana döndürüldü."

        elif tid == "show_this_pc":
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, tweak["reg_key"])
            winreg.SetValueEx(key, tweak["reg_value_name"], 0, winreg.REG_DWORD, 1)  # 1 = hide icon
            winreg.CloseKey(key)
            return True, "Masaüstü 'Bu Bilgisayar' simgesi gizlendi (Varsayılan)."

        elif tid == "disable_uac_dimming":
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, tweak["reg_key"])
            winreg.SetValueEx(key, tweak["reg_value_name"], 0, winreg.REG_DWORD, 1)  # 1 = Secure Desktop
            winreg.CloseKey(key)
            return True, "UAC ekran karartması tekrar açıldı (Varsayılan)."

        elif tid == "disable_hibernation":
            res = subprocess.run("powercfg /hibernate on", shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return True, "Hazırda bekletme özelliği tekrar açıldı (powercfg /h on)."
            return False, f"Hata: {res.stderr.strip() or 'Başarısız'}"

        elif tid == "classic_photo_viewer" or reg_type == "photo_viewer":
            assoc_path = r"SOFTWARE\Microsoft\Windows Photo Viewer\Capabilities\FileAssociations"
            for ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".ico", ".tif", ".tiff"]:
                _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, assoc_path, ext)
            _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\RegisteredApplications", "Windows Photo Viewer")
            return True, "Klasik Fotoğraf Görüntüleyicisi ilişkileri kaldırıldı (Varsayılan)."

        elif tid == "developer_mode":
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, tweak["reg_key"])
            winreg.SetValueEx(key, tweak["reg_value_name"], 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            return True, "Windows Geliştirici Modu kapatıldı (Varsayılan)."

        elif tid == "disable_telemetry":
            _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, tweak["reg_key"], tweak["reg_value_name"])
            return True, "Telemetri kısıtlaması kaldırıldı (Varsayılan)."

        elif tid == "disable_location" or reg_type == "disable_location":
            # 1. Enable Sensor Overrides
            try:
                k1 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}")
                winreg.SetValueEx(k1, "SensorPermissionState", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(k1)
            except Exception:
                pass

            # 2. Remove Policies
            _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableLocation")
            _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableLocationScripting")
            _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableSensors")
            _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableWindowsLocationProvider")

            # 3. Allow App Consent Store (HKLM and HKCU)
            try:
                k3 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location")
                winreg.SetValueEx(k3, "Value", 0, winreg.REG_SZ, "Allow")
                winreg.CloseKey(k3)
            except Exception:
                pass

            try:
                k4 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location")
                winreg.SetValueEx(k4, "Value", 0, winreg.REG_SZ, "Allow")
                winreg.CloseKey(k4)
            except Exception:
                pass

            # 4. Restore Geolocation Service (lfsvc) to Manual (Start=3)
            try:
                k5 = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\lfsvc")
                winreg.SetValueEx(k5, "Start", 0, winreg.REG_DWORD, 3)
                winreg.CloseKey(k5)
            except Exception:
                pass

            return True, "Windows konum servisleri tekrar etkinleştirildi (Varsayılan)."

        elif tid == "clear_icon_cache" or reg_type == "clear_icon_cache":
            return True, "İkon önbelleği sıfırlaması geri alma gerektirmez."

        elif tid == "fast_reboot":
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, tweak["reg_key"])
            winreg.SetValueEx(key, tweak["reg_value_name"], 0, winreg.REG_SZ, "5000")
            winreg.CloseKey(key)
            return True, "Kapanış bekleme süresi 5000ms varsayılanına döndürüldü."

        elif tid == "taskbar_end_task":
            key_path = tweak.get("reg_key") or r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\TaskbarDeveloperSettings"
            val_name = tweak.get("reg_value_name") or "TaskbarEndTask"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, val_name, 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            try:
                k_adv = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(k_adv, "TaskbarDeveloperSettings")
                winreg.CloseKey(k_adv)
            except Exception:
                pass
            return True, "Görev çubuğunda Görevi Sonlandır seçeneği kapatıldı (Varsayılan)."

        # Generic fallback
        elif reg_type == "hkcu":
            _delete_val_safe(winreg.HKEY_CURRENT_USER, tweak["reg_key"], tweak["reg_value_name"])
            return True, "Ayar kaldırıldı (Varsayılan)."

        elif reg_type == "hklm":
            _delete_val_safe(winreg.HKEY_LOCAL_MACHINE, tweak["reg_key"], tweak["reg_value_name"])
            return True, "Ayar kaldırıldı (Varsayılan)."

    except PermissionError:
        return False, "Yönetici izni gerekiyor (Uygulamayı Yönetici Olarak Başlatın)."
    except Exception as e:
        return False, f"Hata: {e}"

    return False, "Bilinmeyen ayar türü"


def clear_icon_cache() -> bool:
    """Purge Windows icon cache databases and restart Explorer cleanly."""
    try:
        no_win = get_no_window_kwargs()
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True, **no_win)
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            icon_cache = os.path.join(local_app, "IconCache.db")
            if os.path.exists(icon_cache):
                try:
                    os.remove(icon_cache)
                except Exception:
                    pass
            exp_dir = os.path.join(local_app, "Microsoft", "Windows", "Explorer")
            if os.path.exists(exp_dir):
                for f in os.listdir(exp_dir):
                    if f.startswith("iconcache"):
                        try:
                            os.remove(os.path.join(exp_dir, f))
                        except Exception:
                            pass
        subprocess.Popen(["explorer.exe"], **no_win)
        return True
    except Exception as e:
        print("Clear icon cache error:", e)
        return False


def restart_explorer():
    """Safely restart Windows Explorer to refresh UI tweaks without spawning console windows."""
    try:
        no_win = get_no_window_kwargs()
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True, **no_win)
        subprocess.Popen(["explorer.exe"], **no_win)
        return True
    except Exception as e:
        print("Explorer restart error:", e)
        return False
