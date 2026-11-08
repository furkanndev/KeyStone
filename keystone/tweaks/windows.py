"""Windows tweaks (registry, powercfg, shell verbs). Ported from KeyStone 2.x."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

from ..core import proc
from .engine import DELETE, Backends, Cmd, Op, Reg, RegKey, Tweak, _ok, annotate, ps

W = "windows"
ADV = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
FOLDER_GUIDS = [
    "{0DB7E03F-FC29-4DC6-9020-FF41B59E513A}",  # 3D Objects
    "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",  # Desktop
    "{f42ee2d3-909f-4907-8871-4c22fc0bf756}",  # Documents
    "{7d83ee9b-2244-4e70-b1f5-5393042af1e4}",  # Downloads
    "{a0c69a99-21c8-4671-8703-7934162fcf1d}",  # Music
    "{0ddd015d-b06c-45d5-8c4c-f59713854639}",  # Pictures
    "{35286a68-3c57-41a1-bbb1-0eae73d76c95}",  # Videos
]
GALLERY = "{e88865ea-0e1c-4e20-9aa6-edcd0212c87c}"
PHOTO_EXTS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".ico", ".tif", ".tiff"]


def _t(id, cat, tr, en, dtr, den, ops, **kw) -> Tweak:
    return Tweak(id, W, cat, {"tr": tr, "en": en}, {"tr": dtr, "en": den}, ops, **kw)


def _folder_ops() -> list:
    ops = []
    for i, node in enumerate([
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions",
        r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions",
    ]):
        for guid in FOLDER_GUIDS:
            ops.append(Reg("HKLM", f"{node}\\{guid}\\PropertyBag", "ThisPCPolicy", "Hide", "SZ",
                           undo="Show", checkable=(i == 0 and guid == FOLDER_GUIDS[2])))
    return ops


def _hibernation_off(_b) -> bool:
    drive = os.environ.get("SystemDrive", "C:")
    return not os.path.exists(os.path.join(drive + os.sep, "hiberfil.sys"))


LOCK_TIMEOUT_SUBGROUP = "7516b95f-f776-4464-8c53-06167f40cc99"
LOCK_TIMEOUT_SETTING = "8ec4b3a5-6868-48c2-be75-4f3044be88a7"
DEFAULT_POWER_SCHEME = "381b4222-f694-41f0-9685-ff5bb260df2e"


def _get_lock_screen_timeout(b: Backends) -> int:
    exists, scheme = b.registry.get("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes", "ActivePowerScheme")
    scheme = scheme or DEFAULT_POWER_SCHEME
    sub_key = rf"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes\{scheme}\{LOCK_TIMEOUT_SUBGROUP}\{LOCK_TIMEOUT_SETTING}"
    exists, val = b.registry.get("HKLM", sub_key, "ACSettingIndex")
    if exists and val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return 60


@dataclass
class LockScreenTimeout(Op):
    """Configures the Windows console lock display-off timeout (Win + L) via powercfg."""
    target_seconds: int
    undo_seconds: int = 60

    def apply(self, b: Backends):
        cmd = ps(
            f"powercfg.exe /SETACVALUEINDEX SCHEME_CURRENT {LOCK_TIMEOUT_SUBGROUP} {LOCK_TIMEOUT_SETTING} {self.target_seconds}; "
            f"powercfg.exe /SETDCVALUEINDEX SCHEME_CURRENT {LOCK_TIMEOUT_SUBGROUP} {LOCK_TIMEOUT_SETTING} {self.target_seconds}; "
            f"powercfg.exe /SETACTIVE SCHEME_CURRENT"
        )
        r = b.run(cmd, timeout=30)
        _ok(r, "powercfg")
        try:
            exists, scheme = b.registry.get("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes", "ActivePowerScheme")
            scheme = scheme or DEFAULT_POWER_SCHEME
            sub_key = rf"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes\{scheme}\{LOCK_TIMEOUT_SUBGROUP}\{LOCK_TIMEOUT_SETTING}"
            b.registry.set("HKLM", sub_key, "ACSettingIndex", "DWORD", self.target_seconds)
            b.registry.set("HKLM", sub_key, "DCSettingIndex", "DWORD", self.target_seconds)
        except Exception:
            pass

    def revert(self, b: Backends):
        cmd = ps(
            f"powercfg.exe /SETACVALUEINDEX SCHEME_CURRENT {LOCK_TIMEOUT_SUBGROUP} {LOCK_TIMEOUT_SETTING} {self.undo_seconds}; "
            f"powercfg.exe /SETDCVALUEINDEX SCHEME_CURRENT {LOCK_TIMEOUT_SUBGROUP} {LOCK_TIMEOUT_SETTING} {self.undo_seconds}; "
            f"powercfg.exe /SETACTIVE SCHEME_CURRENT"
        )
        r = b.run(cmd, timeout=30)
        _ok(r, "powercfg")
        try:
            exists, scheme = b.registry.get("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes", "ActivePowerScheme")
            scheme = scheme or DEFAULT_POWER_SCHEME
            sub_key = rf"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes\{scheme}\{LOCK_TIMEOUT_SUBGROUP}\{LOCK_TIMEOUT_SETTING}"
            b.registry.set("HKLM", sub_key, "ACSettingIndex", "DWORD", self.undo_seconds)
            b.registry.set("HKLM", sub_key, "DCSettingIndex", "DWORD", self.undo_seconds)
        except Exception:
            pass

    def check(self, b: Backends) -> bool:
        current = _get_lock_screen_timeout(b)
        return current != 60


BIOS_REBOOT_SCRIPT = r"""@echo off
:: ============================================================================
:: KeyStone - Reboot Directly to BIOS / UEFI Firmware Settings
:: Bilgisayari yeniden baslatip hicbir tusa basmadan dogrudan BIOS / UEFI
:: ayarlarina yonlendirir.
:: ============================================================================
title KeyStone - Reboot to BIOS / UEFI

:: Administrator rights check (UAC)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Administrator privileges required. Requesting elevation...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cls
echo ============================================================================
echo   KeyStone: Bilgisayar BIOS / UEFI Modunda Yeniden Baslatiliyor
echo ============================================================================
echo.
echo Bilgisayariniz 2 saniye icinde yeniden baslatilacak ve hicbir tusa
echo basmaniza gerek kalmadan dogrudan BIOS / UEFI ayar ekranina girecektir.
echo.
echo (Your computer will restart in 2 seconds directly into UEFI firmware settings.)
echo.

:: Dogrudan UEFI Firmware Setup ekranina yeniden baslat (/r: yeniden baslat, /fw: bellenime gec, /t 2: 2 sn gecikme)
shutdown.exe /r /fw /t 2

if %errorlevel% neq 0 (
    echo.
    echo [BILGI] Dogrudan UEFI anahtari (/fw) basarisiz oldu veya sistem Legacy BIOS modunda.
    echo Gelismis Baslangic Menusune (/o) yonlendiriliyor...
    shutdown.exe /r /o /t 2
)

exit /b
"""


@dataclass
class BiosRebootScriptOp(Op):
    """Saves the Reboot to BIOS script on Desktop when applied."""

    def apply(self, b: Backends):
        desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
        os.makedirs(desktop, exist_ok=True)
        target = os.path.join(desktop, "BIOS_Yeniden_Baslat.bat")
        with open(target, "w", encoding="utf-8") as f:
            f.write(BIOS_REBOOT_SCRIPT)

    def revert(self, b: Backends):
        desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
        target = os.path.join(desktop, "BIOS_Yeniden_Baslat.bat")
        if os.path.exists(target):
            try:
                os.remove(target)
            except OSError:
                pass

    def check(self, b: Backends):
        desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
        target = os.path.join(desktop, "BIOS_Yeniden_Baslat.bat")
        return os.path.exists(target)



def _downloads_pinned(b) -> bool:
    r = b.run(ps(
        "$o=New-Object -ComObject shell.application;"
        "$p=$o.Namespace('shell:::{679f85cb-0220-4080-b29b-5540cc05aab6}').Items()|"
        "?{$_.Path -eq (Join-Path $env:USERPROFILE 'Downloads')};if($p){'1'}else{'0'}"), timeout=30)
    return r.out.strip().endswith("0")


def _photos_legacy_installed(b) -> bool:
    r = b.run(ps("if(Get-AppxPackage -Name 'Microsoft.PhotosLegacy' -ErrorAction SilentlyContinue){'1'}else{'0'}"), timeout=60)
    return r.out.strip().endswith("1")


_appx_lock = threading.Lock()
_appx_seen: tuple[float, set[str]] = (0.0, set())


def _appx_names(b: Backends) -> set[str]:
    """Installed Store packages. Cached briefly: every Appx tweak asks when the page loads."""
    global _appx_seen
    with _appx_lock:
        if time.monotonic() - _appx_seen[0] > 5:
            r = b.run(ps("Get-AppxPackage | ForEach-Object { $_.Name }"), timeout=60)
            _appx_seen = (time.monotonic(), {x.strip() for x in r.out.splitlines() if x.strip()})
        return _appx_seen[1]


def _appx_forget() -> None:
    global _appx_seen
    with _appx_lock:
        _appx_seen = (0.0, set())


@dataclass
class Appx(Op):
    """Remove Store packages for this user; revert reinstalls ``store_id`` from the Store."""
    names: list[str]
    store_id: str = ""

    def apply(self, b):
        script = "; ".join(f"Get-AppxPackage -Name '{n}' | Remove-AppxPackage -ErrorAction Stop" for n in self.names)
        r = b.run(ps(script), timeout=300)
        _appx_forget()
        _ok(r, "Remove-AppxPackage")

    def revert(self, b):
        if self.store_id:
            r = b.run(["winget", "install", "--id", self.store_id, "--source", "msstore", "--accept-package-agreements",
                       "--accept-source-agreements", "--disable-interactivity"], timeout=900)
            _appx_forget()
            _ok(r, "winget")

    def check(self, b):
        return not set(self.names) & _appx_names(b)


def _onedrive_gone(_b) -> bool:
    local = os.environ.get("LOCALAPPDATA", "")
    return not any(os.path.isfile(os.path.join(d, "OneDrive.exe")) for d in (
        os.path.join(local, "Microsoft", "OneDrive"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft OneDrive"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft OneDrive")))


def _remove(id, tr, en, names, store_id="", **kw) -> Tweak:
    """Removes one pre-installed app; without a Store id it cannot be undone from here."""
    return _t(id, "debloat", f"{tr} uygulamasını kaldır", f"Remove {en}",
              f"{tr} uygulamasını bu kullanıcı için kaldırır." + (" Geri alınınca Microsoft Store'dan yeniden kurulur."
                                                                  if store_id else " Geri alınamaz; gerekirse Store'dan elle kurulur."),
              f"Removes {en} for this user." + (" Reverting reinstalls it from the Microsoft Store."
                                                if store_id else " Cannot be undone here; reinstall it from the Store by hand."),
              [Appx(names, store_id)], action=not store_id, **kw)


def _clear_icon_cache() -> list[str]:
    return ps(
        "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue;"
        "Remove-Item \"$env:LOCALAPPDATA\\IconCache.db\" -Force -ErrorAction SilentlyContinue;"
        "Remove-Item \"$env:LOCALAPPDATA\\Microsoft\\Windows\\Explorer\\iconcache*\" -Force -ErrorAction SilentlyContinue;"
        "Start-Process explorer.exe")


_feature_cache: dict[str, int] = {}
_feature_cache_time: float = 0.0


def _clear_feature_cache() -> None:
    global _feature_cache, _feature_cache_time
    _feature_cache.clear()
    _feature_cache_time = 0.0


def _get_feature_states(b: Backends) -> dict[str, int]:
    global _feature_cache, _feature_cache_time
    now = time.monotonic()
    if _feature_cache and (now - _feature_cache_time < 5.0):
        return _feature_cache
    try:
        cmd = ps("Get-CimInstance Win32_OptionalFeature | Select-Object -Property Name, InstallState | ConvertTo-Csv -NoTypeInformation")
        r = b.run(cmd, timeout=15)
        if r.ok:
            mapping = {}
            for line in r.out.splitlines():
                line = line.strip()
                if not line or line.startswith('"Name"'):
                    continue
                parts = [p.strip('"') for p in line.split(',')]
                if len(parts) >= 2 and parts[1].isdigit():
                    mapping[parts[0]] = int(parts[1])
            if mapping:
                _feature_cache = mapping
                _feature_cache_time = now
                return mapping
    except Exception:
        pass
    return _feature_cache


@dataclass
class DismFeature(Op):
    """Windows Optional Feature managed via DISM."""
    features: list[str]

    def apply(self, b: Backends):
        for f in self.features:
            cmd = ["dism.exe", "/Online", "/Enable-Feature", f"/FeatureName:{f}", "/All", "/NoRestart"]
            r = b.run(cmd, timeout=300)
            if r.code not in (0, 3010):
                _ok(r, f"dism enable {f}")
        _clear_feature_cache()

    def revert(self, b: Backends):
        for f in self.features:
            cmd = ["dism.exe", "/Online", "/Disable-Feature", f"/FeatureName:{f}", "/NoRestart"]
            r = b.run(cmd, timeout=300)
            if r.code not in (0, 3010):
                _ok(r, f"dism disable {f}")
        _clear_feature_cache()

    def check(self, b: Backends) -> bool | None:
        cache = _get_feature_states(b)
        if not cache:
            return None
        results = [cache.get(f) == 1 for f in self.features if f in cache]
        if len(results) != len(self.features):
            return None
        return all(results)


TWEAKS: list[Tweak] = [
    _t("classic_context_menu", "interface",
       "Klasik sağ tık menüsü", "Classic context menu",
       "Windows 11'in 'Daha fazla seçenek göster' adımını kaldırır, tam menüyü doğrudan açar.",
       "Skips Windows 11's 'Show more options' step and opens the full menu directly.",
       [RegKey("HKCU", r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32",
               delete_root=r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}")],
       restart="explorer", recommended=True),
    _t("taskbar_end_task", "interface",
       "Görev çubuğunda 'Görevi sonlandır'", "Taskbar 'End task'",
       "Görev çubuğu simgesine sağ tıklayınca yanıt vermeyen uygulamayı kapatma seçeneği ekler.",
       "Adds 'End task' to taskbar icons so frozen apps close without Task Manager.",
       [Reg("HKCU", ADV + r"\TaskbarDeveloperSettings", "TaskbarEndTask", 1, undo=0)],
       restart="explorer", recommended=True),
    _t("menu_show_delay", "interface",
       "Menü açılış gecikmesini kaldır (MenuShowDelay)", "Remove menu show delay (MenuShowDelay)",
       "Başlat ve sağ tık menülerinin açılış gecikmesini sıfırlayarak (0 ms) menülerin anında açılmasını sağlar.",
       "Sets MenuShowDelay to 0 ms so start and context submenus appear instantly without animation lag.",
       [Reg("HKCU", r"Control Panel\Desktop", "MenuShowDelay", "0", "SZ", undo="400")],
       recommended=True),
    _t("show_file_extensions", "interface",
       "Dosya uzantılarını göster", "Show file extensions",
       "Dosya Gezgini'nde .exe, .pdf gibi uzantıları her zaman gösterir.",
       "Always show extensions such as .exe and .pdf in File Explorer.",
       [Reg("HKCU", ADV, "HideFileExt", 0, undo=1)], restart="explorer", recommended=True),
    _t("show_hidden_files", "interface",
       "Gizli dosyaları göster", "Show hidden files",
       "Gizli dosya ve klasörleri Dosya Gezgini'nde görünür yapar.",
       "Make hidden files and folders visible in File Explorer.",
       [Reg("HKCU", ADV, "Hidden", 1, undo=2)], restart="explorer"),
    _t("dark_mode", "interface",
       "Koyu tema", "Dark mode",
       "Sistem ve uygulamalar için koyu temayı açar.",
       "Turn on dark mode for Windows and apps.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "AppsUseLightTheme", 0, undo=1),
        Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "SystemUsesLightTheme", 0, undo=1)]),
    _t("remove_user_folders", "interface",
       "Bu Bilgisayar'daki kullanıcı klasörlerini gizle", "Hide user folders in This PC",
       "Belgeler, Resimler gibi 7 klasörü gizler; yalnızca diskler görünür.",
       "Hides the 7 user folders so This PC shows only drives.",
       _folder_ops(), restart="explorer", admin=True),
    _t("unpin_downloads_quick_access", "interface",
       "İndirilenler'i Hızlı Erişim'den kaldır", "Unpin Downloads from Home",
       "Dosya Gezgini'nin sol menüsündeki sabit İndirilenler kısayolunu kaldırır; dosyalar silinmez.",
       "Removes the pinned Downloads shortcut from File Explorer's navigation pane. No files are deleted.",
       [Cmd(ps("$o=New-Object -ComObject shell.application;"
               "($o.Namespace('shell:::{679f85cb-0220-4080-b29b-5540cc05aab6}').Items()|"
               "?{$_.Path -eq (Join-Path $env:USERPROFILE 'Downloads')}).InvokeVerb('unpinfromhome')"),
            ps("$o=New-Object -ComObject shell.application;"
               "$o.Namespace((Join-Path $env:USERPROFILE 'Downloads')).Self.InvokeVerb('pintohome')"),
            probe=_downloads_pinned)]),
    _t("remove_gallery", "interface",
       "Gezgin'den Galeri'yi kaldır", "Remove Gallery from Explorer",
       "Windows 11 gezinti panelindeki Galeri simgesini kaldırır.",
       "Removes the Gallery entry from the Windows 11 navigation pane.",
       [Reg("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\NonEnum", GALLERY, 1),
        Reg("HKLM", rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace\{GALLERY}", "HiddenByDefault", 1, checkable=False),
        Reg("HKCU", rf"Software\Classes\CLSID\{GALLERY}", "System.IsPinnedToNameSpaceTree", 0, checkable=False)],
       restart="explorer", admin=True),
    _t("show_this_pc", "interface",
       "Masaüstünde 'Bu Bilgisayar'", "'This PC' on desktop",
       "Kurulumdan sonra kaybolan Bu Bilgisayar simgesini masaüstüne ekler.",
       "Puts the This PC icon back on the desktop.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel",
            "{20D04FE0-3AEA-1069-A2D8-08002B30309D}", 0, undo=1)],
       restart="explorer", recommended=True),
    _t("photos_legacy", "interface",
       "Microsoft Fotoğraflar (Eski)", "Microsoft Photos Legacy",
       "Hızlı açılan klasik Fotoğraflar uygulamasını Microsoft Store'dan kurar.",
       "Installs the fast classic Photos app from the Microsoft Store.",
       [Cmd(["winget", "install", "--id", "9NV2L4XVMCXM", "--source", "msstore",
             "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"],
            ["winget", "uninstall", "--id", "9NV2L4XVMCXM", "--disable-interactivity"],
            probe=_photos_legacy_installed)], recommended=True),
    _t("disable_bing_search", "performance",
       "Başlat menüsünde web aramasını kapat", "No web results in Start",
       "Başlat aramasını yalnızca yerel tutar; daha hızlı ve daha az veri gönderir.",
       "Keeps Start search local: faster and sends less data.",
       [Reg("HKCU", r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions", 1),
        Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled", 0, undo=1)],
       restart="explorer", recommended=True),
    _t("disable_telemetry", "privacy",
       "Telemetriyi en aza indir", "Minimise telemetry",
       "Microsoft'a gönderilen tanılama verilerini izin verilen en düşük seviyeye çeker.",
       "Sets diagnostic data to the lowest level Windows allows.",
       [Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0)],
       admin=True, recommended=True),
    _t("disable_location", "privacy",
       "Konum servislerini kapat", "Turn off location services",
       "Windows'un ve uygulamaların konumunuza erişimini kapatır.",
       "Stops Windows and apps from accessing your location.",
       [Reg("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}",
            "SensorPermissionState", 0, undo=1, checkable=False),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableLocation", 1),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableLocationScripting", 1, checkable=False),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "DisableWindowsLocationProvider", 1, checkable=False),
        Reg("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
            "Value", "Deny", "SZ", undo="Allow", checkable=False),
        Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
            "Value", "Deny", "SZ", undo="Allow", checkable=False),
        Reg("HKLM", r"SYSTEM\CurrentControlSet\Services\lfsvc", "Start", 4, undo=3, checkable=False)],
       admin=True, recommended=True),
    _t("remove_onedrive", "debloat",
       "OneDrive'ı kaldır", "Remove OneDrive",
       "OneDrive'ı kaldırır ve yeniden kurulmasını engeller. Yalnızca bulutta duran dosyalar bu bilgisayarda açılamaz olur; "
       "önce önemli olanları indirin. Bulut kopyaları silinmez.",
       "Uninstalls OneDrive and blocks it from coming back. Cloud-only files stop being available on this PC, so download "
       "what you need first. Cloud copies are not deleted.",
       [Cmd(ps("taskkill /F /IM OneDrive.exe 2>$null;"
               "winget uninstall --id Microsoft.OneDrive --silent --accept-source-agreements --disable-interactivity;"
               "if ($LASTEXITCODE -notin 0, -1978335212) { exit $LASTEXITCODE } else { exit 0 }"),
            ["winget", "install", "--id", "Microsoft.OneDrive", "--source", "winget", "--silent",
             "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"],
            probe=_onedrive_gone),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\OneDrive", "DisableFileSyncNGSC", 1)],
       admin=True, risk="high"),
    _t("remove_copilot", "debloat",
       "Copilot'u kaldır", "Remove Copilot",
       "Copilot uygulamasını kaldırır, görev çubuğu düğmesini gizler ve ilkeyle kapatır.",
       "Removes the Copilot app, hides its taskbar button and turns it off by policy.",
       [Appx(["Microsoft.Copilot"], "XP9CXNGPPJ97XX"),
        Reg("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1),
        Reg("HKCU", ADV, "ShowCopilotButton", 0, undo=1, checkable=False)],
       restart="explorer"),
    _t("disable_recall", "debloat",
       "Recall'u kapat", "Turn off Recall",
       "Ekran görüntüsü kaydeden Windows Recall özelliğini ilkeyle kapatır.",
       "Turns off Windows Recall, which saves screen snapshots, by policy.",
       [Reg("HKCU", r"Software\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", 1),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI", "AllowRecallEnablement", 0)],
       admin=True),
    _t("disable_widgets", "debloat",
       "Pencere öğelerini kapat", "Turn off Widgets",
       "Görev çubuğundaki haber ve hava durumu panosunu ilkeyle kapatır.",
       "Turns off the taskbar news and weather board by policy.",
       [Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Dsh", "AllowNewsAndInterests", 0)],
       restart="explorer", admin=True),
    _t("disable_suggested_apps", "debloat",
       "Önerilen uygulamaları durdur", "Stop suggested apps",
       "Windows'un Candy Crush gibi uygulamaları kendiliğinden kurmasını ilkeyle engeller.",
       "Stops Windows from installing apps such as Candy Crush on its own, by policy.",
       [Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableWindowsConsumerFeatures", 1)],
       admin=True),
    _remove("remove_teams", "Microsoft Teams", "Microsoft Teams", ["MSTeams", "MicrosoftTeams"], "XP8BT8DW290MPQ"),
    _remove("remove_outlook_new", "Yeni Outlook", "the new Outlook", ["Microsoft.OutlookForWindows"], "9NRX63209R7B"),
    _remove("remove_clipchamp", "Clipchamp", "Clipchamp", ["Clipchamp.Clipchamp"], "9P1J8S7CCWWT"),
    _remove("remove_weather", "MSN Hava Durumu", "MSN Weather", ["Microsoft.BingWeather"], "9WZDNCRFJ3Q2"),
    _remove("remove_feedback_hub", "Geri Bildirim Merkezi", "Feedback Hub", ["Microsoft.WindowsFeedbackHub"], "9NBLGGH4R32N"),
    _remove("remove_power_automate", "Power Automate", "Power Automate", ["Microsoft.PowerAutomateDesktop"], "9NFTCH6J7FHV"),
    _remove("remove_bing_news", "Microsoft Haberler", "Microsoft News", ["Microsoft.BingNews"]),
    _remove("remove_solitaire", "Solitaire", "Solitaire", ["Microsoft.MicrosoftSolitaireCollection"]),
    _t("disable_uac_prompts", "system",
       "UAC onaylarını kapat", "Disable UAC prompts",
       "Yönetici onay pencerelerini kaldırır. Güvenliği düşürür; yalnızca ne yaptığınızı biliyorsanız açın.",
       "Removes admin consent prompts. Lowers security — only if you know why you need it.",
       [Reg("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "ConsentPromptBehaviorAdmin", 0, undo=5)],
       admin=True, risk="high"),
    _t("disable_hibernation", "system",
       "Hazırda bekletmeyi kapat", "Disable hibernation",
       "RAM boyutu kadar yer kaplayan hiberfil.sys dosyasını kaldırır.",
       "Removes hiberfil.sys and reclaims disk space equal to your RAM.",
       [Cmd(["powercfg", "/hibernate", "off"], ["powercfg", "/hibernate", "on"], probe=lambda b: _hibernation_off(b))],
       admin=True),
    _t("lock_screen_timeout_unhide", "system",
       "Kilit ekranı zaman aşımını Denetim Masası'nda göster", "Unhide lock screen timeout in Control Panel",
       "Microsoft'un varsayılan olarak gizlediği 'Konsol kilidi ekran kapatma zaman aşımı' ayarını Denetim Masası Gelişmiş Güç Seçenekleri > Ekran menüsünde kalıcı olarak görünür yapar.",
       "Permanently reveals the hidden 'Console lock display off timeout' setting in Windows Control Panel Advanced Power Options under Display.",
       [Reg("HKLM", rf"SYSTEM\CurrentControlSet\Control\Power\PowerSettings\{LOCK_TIMEOUT_SUBGROUP}\{LOCK_TIMEOUT_SETTING}", "Attributes", 2, undo=1)],
       admin=True, recommended=True),
    _t("lock_screen_timeout_extend", "system",
       "Kilit ekranı kapanma süresi", "Lock screen timeout",
       "Bilgisayar kilitlendiğinde (Win + L) ekranın ne zaman kararacağını belirler.",
       "Set how long before the display turns off when the computer is locked (Win + L).",
       [LockScreenTimeout(1800, 60)],
       recommended=True),
    _t("fast_reboot", "system",
       "Kapanışı hızlandır", "Faster shutdown",
       "Kapanırken yanıt vermeyen uygulamaları bekleme süresini 5 sn'den 2 sn'ye indirir.",
       "Cuts the wait for hung apps at shutdown from 5 s to 2 s.",
       [Reg("HKCU", r"Control Panel\Desktop", "WaitToKillAppTimeout", "2000", "SZ", undo="5000")],
       recommended=True),
    _t("long_paths", "developer",
       "Uzun dosya yolları", "Long file paths",
       "260 karakterlik yol sınırını kaldırır (node_modules, derin projeler için).",
       "Lifts the 260-character path limit (node_modules, deep project trees).",
       [Reg("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "LongPathsEnabled", 1, undo=0)],
       admin=True),
    _t("developer_mode", "developer",
       "Geliştirici modu", "Developer mode",
       "İmzasız paketlerin yüklenmesine ve sembolik bağlantılara izin verir.",
       "Allows sideloading unsigned packages and creating symlinks without admin.",
       [Reg("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock", "AllowDevelopmentWithoutDevLicense", 1, undo=0)],
       admin=True),
    _t("wsl2", "developer",
       "WSL 2 (Linux için Windows Alt Sistemi)", "WSL 2 (Windows Subsystem for Linux)",
       "Linux dağıtımlarını ve Docker'ı yerel çekirdek performansıyla çalıştırmak için WSL ve Sanal Makine Platformunu açar.",
       "Enables Windows Subsystem for Linux and Virtual Machine Platform to run native Linux distributions.",
       [DismFeature(["Microsoft-Windows-Subsystem-Linux", "VirtualMachinePlatform"])],
       admin=True, recommended=True),
    _t("virtual_machine_platform", "developer",
       "Sanal Makine Platformu", "Virtual Machine Platform",
       "WSL 2, WSA ve sanallaştırma tabanlı araçlar için temel hipervizör platform desteğini açar.",
       "Enables platform support for virtual machines, required by WSL 2, WSA, and modern hypervisors.",
       [DismFeature(["VirtualMachinePlatform"])],
       admin=True),
    _t("hyper_v", "developer",
       "Hyper-V Sanallaştırma", "Hyper-V Virtualization",
       "Yerel donanım destekli sanal makineler (VM) oluşturmak ve yönetmek için Hyper-V bileşenlerini açar.",
       "Enables the native Microsoft Hyper-V hypervisor and management tools to run virtual machines.",
       [DismFeature(["Microsoft-Hyper-V-All"])],
       admin=True),
    _t("windows_hypervisor_platform", "developer",
       "Windows Hipervizör Platformu", "Windows Hypervisor Platform",
       "VirtualBox, QEMU ve Android Emulator gibi üçüncü taraf sanallaştırma yazılımlarının Windows ile uyumlu çalışmasını sağlar.",
       "Allows third-party virtualization software (VirtualBox, QEMU, Android Emulator) to run on top of Windows Hypervisor.",
       [DismFeature(["HypervisorPlatform"])],
       admin=True),
    _t("windows_sandbox", "system",
       "Windows Korumalı Alanı (Sandbox)", "Windows Sandbox",
       "Bilinmeyen veya şüpheli uygulamaları güvenle denemek için tek kullanımlık izole masaüstü ortamını açar.",
       "Provides a lightweight, isolated disposable desktop environment to safely test untrusted apps.",
       [DismFeature(["Containers-DisposableClientVM"])],
       admin=True),
    _t("telnet_client", "system",
       "Telnet İstemcisi", "Telnet Client",
       "Ağ aygıtlarını ve uzak sunucu bağlantı noktalarını sınamak için klasik Telnet komut satırı istemcisini açar.",
       "Enables the classic command-line Telnet client to test network ports and connect to remote hosts.",
       [DismFeature(["TelnetClient"])],
       admin=True),
    _t("netfx3", "system",
       ".NET Framework 3.5 (2.0 ve 3.0 dahil)", ".NET Framework 3.5 (includes 2.0 & 3.0)",
       "Eski Windows programları ve klasik oyunlar için gerekli .NET 2.0/3.0/3.5 çalışma zamanını açar.",
       "Enables runtime support for older applications and legacy games that require .NET 2.0, 3.0, and 3.5.",
       [DismFeature(["NetFx3"])],
       admin=True),
    _t("reboot_to_bios_script", "system",
       "BIOS'a Geçiş Scripti İndir (Reboot to UEFI)", "Download Reboot to BIOS Script",
       "Çift tıklandığında hiçbir tuşa basmadan doğrudan BIOS / UEFI ekranına yeniden başlatan (.bat) dosyasını istediğiniz konuma indirir.",
       "Downloads a self-elevating (.bat) script to your chosen location that directly restarts your PC into UEFI/BIOS firmware without pressing any keys.",
       [BiosRebootScriptOp()],
       action=True),
    _t("clear_icon_cache", "maintenance",
       "Simge önbelleğini yenile", "Rebuild icon cache",
       "Bozuk ya da beyaz görünen simgeleri düzeltmek için IconCache.db'yi sıfırlar.",
       "Resets IconCache.db to fix broken or blank icons.",
       [Cmd(_clear_icon_cache())], action=True),
    _t("disable_activity_history", "privacy",
       "Etkinlik geçmişini kapat", "Disable activity history",
       "Windows'un faaliyetlerinizi kaydetmesini engeller. Pano geçmişi etkin kalır.",
       "Stops Windows from recording your activities. Clipboard history remains enabled.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_TrackProgs", 0, undo=1)],
       recommended=True),
    _t("disable_advertising_id", "privacy",
       "Reklam kimliğini devre dışı bırak", "Disable advertising ID",
       "Microsoft'un size yönelik hedefli reklamlar sunmasında kullandığı kimliği kaldırır.",
       "Disables the advertising ID used by Microsoft to track you for targeted ads.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0, undo=1),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo", "DisabledForUser", 1)],
       admin=True, recommended=True),
    _t("disable_input_personalization", "privacy",
       "Giriş kişiselleştirmesini kapat", "Disable input personalization",
       "Yazı ve mürekkep verilerinin kişiselleştirme için toplanmasını engeller.",
       "Stops handwriting, inking, and keyboard input data collection for personalization.",
       [Reg("HKCU", r"Software\Microsoft\InputPersonalization", "RestrictImplicitInkCollection", 1, undo=0),
        Reg("HKCU", r"Software\Microsoft\InputPersonalization", "RestrictImplicitTextCollection", 1, undo=0),
        Reg("HKCU", r"Software\Microsoft\InputPersonalization\TrainedDataStore", "HarvestContacts", 0, undo=1)],
       recommended=True),
    _t("disable_delivery_optimization", "performance",
       "Teslim Optimizasyonunu kapat", "Disable Delivery Optimization",
       "Windows ve uygulamalar için bant genişliği paylaşımını kapatır; indiriş hızını artırır.",
       "Disables bandwidth sharing for Windows/app updates; speeds up your downloads.",
       [Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization", "DODownloadMode", 0)],
       admin=True),
    _t("disable_speech_privacy", "privacy",
       "Ses veri toplanmasını kapat", "Disable speech data collection",
       "Bulut tabanlı konuşma tanıma verilerinin toplanmasını engeller.",
       "Stops cloud-based speech recognition data from being collected and sent.",
       [Reg("HKCU", r"Software\Microsoft\Speech_OneCore\Preferences", "ModelDownloadAllowed", 0, undo=1)],
       recommended=True),
    _t("disable_tailored_experiences", "privacy",
       "Kişiselleştirilmiş deneyimi kapat", "Disable tailored experiences",
       "Tanılama verilerine dayalı hedefli reklam ve öneriler devre dışı bırakır.",
       "Disables personalized ads and recommendations based on diagnostic data.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Privacy", "TailoredExperiencesAllowed", 0, undo=1)],
       recommended=True),
    _t("storage_sense_disable", "performance",
       "Depolama Duygusu'nu devre dışı bırak", "Disable Storage Sense",
       "Windows'un otomatik olarak geçici dosyaları silmesini engeller; elle temizle.",
       "Stops Windows from auto-deleting temp files; gives you manual control.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy", "01", 0, undo=1)],
       recommended=False),
    _t("visual_effects_performance", "performance",
       "Görsel efektleri kapat", "Disable visual effects",
       "Animasyonlar ve şeffaflık efektlerini kapat; ekran hızını artır.",
       "Disables animations and transparency effects for maximum performance.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 2, undo=3)],
       restart="explorer"),
    _t("disable_background_apps", "performance",
       "Arka plan uygulamalarını kapat", "Disable background apps",
       "Uygulamaların kapalıyken arka planda çalışmasını engeller; pil ve bellek tasarrufu sağlar.",
       "Stops apps from running in the background when closed; saves battery and memory.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", 1, undo=0)]),
    _t("disable_notification_center", "interface",
       "Bildirim merkezini ve toast bildirimlerini kapat", "Disable notification center and toasts",
       "Sistem tepsisi bildirimlerini ve takvim/bildirim panelini kapatır.",
       "Turns off system tray notifications and the notification/calendar panel.",
       [Reg("HKCU", r"Software\Policies\Microsoft\Windows\Explorer", "DisableNotificationCenter", 1),
        Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\PushNotifications", "ToastEnabled", 0, undo=1)],
       restart="explorer"),
    _t("realtime_clock_utc", "system",
       "Saati UTC olarak tut", "Set hardware clock to UTC",
       "Windows'un donanım saatini UTC kabul etmesini sağlar; Linux ile çift önyüklemede saat kaymasını önler.",
       "Makes Windows treat the hardware clock as UTC; avoids clock drift when dual-booting with Linux.",
       [Reg("HKLM", r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation", "RealTimeIsUniversal", 1, "QWORD", undo=0)],
       admin=True),
    _t("disable_wpbt", "privacy",
       "WPBT çalıştırmayı kapat", "Disable WPBT execution",
       "Bellenimin Windows açılırken program yerleştirmesine izin veren Platform Binary Table'ı devre dışı bırakır.",
       "Disables the Windows Platform Binary Table, which lets firmware drop programs into Windows at boot.",
       [Reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager", "DisableWpbtExecution", 1)],
       admin=True),
    _t("block_device_metadata", "privacy",
       "Aygıt eşlik uygulamalarını engelle", "Prevent device companion apps",
       "Windows'un aygıt bilgisi ve eşlik uygulamalarını ağdan indirmesini engeller.",
       "Stops Windows from downloading device info and companion apps from the network.",
       [Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Device Metadata", "PreventDeviceMetadataFromNetwork", 1)],
       admin=True),
    _t("block_oem_driver_autoinstall", "privacy",
       "Razer/Logitech otomatik kurulumunu durdur", "Stop Razer/Logitech auto-install",
       "Aygıt takıldığında Windows'un üretici yazılımlarını (Razer Synapse vb.) kendiliğinden kurmasını engeller.",
       "Stops Windows from auto-installing vendor software (Razer Synapse and similar) when a device is plugged in.",
       [Reg("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching", "SearchOrderConfig", 0, undo=1),
        Reg("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Device Installer", "DisableCoInstallers", 1, undo=0)],
       admin=True),
    _t("disable_ipv6", "system",
       "IPv6'yı kapat", "Disable IPv6",
       "IPv6 bileşenlerini kapatır. Bazı ağlarda sorun çıkarabilir.",
       "Turns off IPv6 components. May cause problems on some networks.",
       [Reg("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters", "DisabledComponents", 255, undo=0)],
       admin=True, risk="medium"),
    _t("prefer_ipv4", "system",
       "IPv4'ü tercih et", "Prefer IPv4 over IPv6",
       "IPv6'yı kapatmadan IPv4 bağlantılarına öncelik verir.",
       "Prefers IPv4 connections without turning IPv6 off.",
       [Reg("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters", "DisabledComponents", 32, undo=0)],
       admin=True),
    _t("disable_rdp_unsigned_warning", "system",
       "RDP imzasız dosya uyarısını kapat", "Disable RDP unsigned file warnings",
       "İmzasız .rdp dosyaları açılırken çıkan uyarı pencerelerini kaldırır.",
       "Removes the warning dialogs shown when opening unsigned .rdp files.",
       [Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services\Client", "RedirectionWarningDialogVersion", 1),
        Reg("HKCU", r"SOFTWARE\Microsoft\Terminal Server Client", "RdpLaunchConsentAccepted", 1)],
       admin=True),
    _t("start_menu_old_layout", "interface",
       "Eski Başlat menüsü düzeni", "Previous Start menu layout",
       "Windows 11'in yeni Başlat menüsü yerine önceki düzeni geri getirir.",
       "Brings back the previous Start menu layout instead of the new Windows 11 one.",
       [Reg("HKLM", r"SYSTEM\ControlSet001\Control\FeatureManagement\Overrides\8\3036241548", "EnabledState", 1)],
       admin=True, restart="explorer"),
    _t("disable_home_gallery_nav", "interface",
       "Gezginde Ana Sayfa ve Galeri'yi gizle", "Hide Home and Gallery in Explorer",
       "Dosya Gezgini gezinti bölmesinden Ana Sayfa ile Galeri'yi kaldırır ve Bu Bilgisayar'da açar.",
       "Removes Home and Gallery from the File Explorer navigation pane and opens This PC.",
       [Reg("HKCU", r"Software\Classes\CLSID\{f874310e-b6b7-47dc-bc84-b9e6b38f5903}", "System.IsPinnedToNameSpaceTree", 0),
        Reg("HKCU", r"Software\Classes\CLSID\{e88865ea-0e1c-4e20-9aa6-edcd0212c87c}", "System.IsPinnedToNameSpaceTree", 0),
        Reg("HKCU", ADV, "LaunchTo", 1, checkable=False)],
       restart="explorer"),
    _t("detailed_bsod", "system",
       "Ayrıntılı mavi ekran", "Verbose BSOD",
       "Mavi ekranda hata parametrelerini gösterir ve gülen yüzü kaldırır.",
       "Shows error parameters on the blue screen and removes the emoticon.",
       [Reg("HKLM", r"SYSTEM\CurrentControlSet\Control\CrashControl", "DisplayParameters", 1, undo=0),
        Reg("HKLM", r"SYSTEM\CurrentControlSet\Control\CrashControl", "DisableEmoticon", 1, undo=0)],
       admin=True),
    _t("verbose_logon", "system",
       "Ayrıntılı oturum açma iletileri", "Verbose logon messages",
       "Oturum açma ve kapatma sırasında ayrıntılı durum iletilerini gösterir.",
       "Shows detailed status messages during sign-in and shutdown.",
       [Reg("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "VerboseStatus", 1, undo=0)],
       admin=True),
    _t("battery_percentage", "interface",
       "Pil yüzdesini göster", "Show battery percentage",
       "Görev çubuğundaki pil simgesinin yanında yüzdeyi gösterir.",
       "Shows the percentage next to the taskbar battery icon.",
       [Reg("HKCU", ADV, "IsBatteryPercentageEnabled", 1)],
       restart="explorer"),
    _t("scrollbars_always_visible", "interface",
       "Kaydırma çubukları hep görünsün", "Always show scrollbars",
       "Kaydırma çubuklarının kendiliğinden gizlenmesini kapatır.",
       "Stops scrollbars from hiding themselves.",
       [Reg("HKCU", r"Control Panel\Accessibility", "DynamicScrollbars", 0, undo=1)]),
    _t("disable_mouse_acceleration", "interface",
       "Fare ivmesini kapat", "Disable mouse acceleration",
       "Fare hızlandırmasını (işaretçi duyarlılığını artır) kapatır; oyunlarda tutarlı imleç verir.",
       "Turns off pointer acceleration (Enhance pointer precision) for consistent aim in games.",
       [Reg("HKCU", r"Control Panel\Mouse", "MouseSpeed", "0", "SZ", undo="1"),
        Reg("HKCU", r"Control Panel\Mouse", "MouseThreshold1", "0", "SZ", undo="6"),
        Reg("HKCU", r"Control Panel\Mouse", "MouseThreshold2", "0", "SZ", undo="10")],
       recommended=True),
    _t("numlock_on_startup", "interface",
       "Num Lock açık başlasın", "Num Lock on at startup",
       "Oturum açıldığında Num Lock tuşunu açık başlatır.",
       "Starts with Num Lock turned on after sign-in.",
       [Reg("HKCU", r"Control Panel\Keyboard", "InitialKeyboardIndicators", "2", "SZ", undo="0")]),
    _t("disable_sticky_keys", "interface",
       "Yapışkan tuşları kapat", "Disable Sticky Keys",
       "Shift'e beş kez basınca çıkan Yapışkan Tuşlar penceresini kapatır.",
       "Turns off the Sticky Keys prompt triggered by pressing Shift five times.",
       [Reg("HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags", "506", "SZ", undo="510")],
       recommended=True),
    _t("settings_home_hide", "interface",
       "Ayarlar ana sayfasını gizle", "Hide Settings home page",
       "Ayarlar uygulamasındaki öneri dolu ana sayfayı gizler.",
       "Hides the suggestion-filled home page in the Settings app.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "SettingsPageVisibility", "hide:home", "SZ")]),
    _t("disable_lock_screen", "interface",
       "Kilit ekranını kapat", "Disable lock screen",
       "Kilit ekranını atlayıp doğrudan oturum açma ekranına gider.",
       "Skips the lock screen and goes straight to the sign-in screen.",
       [Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "NoLockScreen", 1)],
       admin=True),
    _t("hide_start_recommendations", "interface",
       "Başlat önerilerini gizle", "Hide Start menu recommendations",
       "Başlat menüsündeki 'Önerilen' bölümünü gizler.",
       "Hides the 'Recommended' section of the Start menu.",
       [Reg("HKLM", r"SOFTWARE\Microsoft\PolicyManager\current\device\Start", "HideRecommendedSection", 1, undo=0),
        Reg("HKLM", r"SOFTWARE\Microsoft\PolicyManager\current\device\Education", "IsEducationEnvironment", 1, undo=0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Explorer", "HideRecommendedSection", 1, undo=0)],
       admin=True, restart="explorer"),
    _t("taskbar_align_left", "interface",
       "Görev çubuğunu sola hizala", "Left-align the taskbar",
       "Windows 11 görev çubuğu simgelerini ortada değil solda gösterir.",
       "Shows Windows 11 taskbar icons on the left instead of centered.",
       [Reg("HKCU", ADV, "TaskbarAl", 0, undo=1)],
       restart="explorer"),
    _t("taskbar_hide_search", "interface",
       "Görev çubuğu arama kutusunu gizle", "Hide taskbar search",
       "Görev çubuğundaki arama kutusunu/simgesini kaldırır.",
       "Removes the search box/icon from the taskbar.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "SearchboxTaskbarMode", 0, undo=1)],
       restart="explorer"),
    _t("taskbar_hide_task_view", "interface",
       "Görev Görünümü düğmesini gizle", "Hide Task View button",
       "Görev çubuğundaki Görev Görünümü düğmesini kaldırır.",
       "Removes the Task View button from the taskbar.",
       [Reg("HKCU", ADV, "ShowTaskViewButton", 0, undo=1)],
       restart="explorer"),
    _t("enable_game_mode", "performance",
       "Oyun Modu'nu aç", "Enable Game Mode",
       "Oyun sırasında Windows'un arka plan işlerine öncelik vermesini azaltır.",
       "Reduces background activity priority while you play.",
       [Reg("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode", 1, undo=0),
        Reg("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1, undo=0)],
       recommended=True),
    _t("disable_window_snapping", "interface",
       "Pencere yakalamayı kapat", "Disable window snapping",
       "Pencereleri ekran kenarına sürüklerken otomatik yerleştirmeyi kapatır.",
       "Turns off automatic snapping when dragging windows to screen edges.",
       [Reg("HKCU", r"Control Panel\Desktop", "WindowArrangementActive", "0", "SZ", undo="1")]),
    _t("disable_svchost_splitting", "performance",
       "svchost bölünmesini kapat", "Disable svchost splitting",
       "Hizmetlerin ayrı svchost işlemlerine bölünmesini kapatır; işlem sayısını azaltır (bellek fazlaysa).",
       "Stops services from being split into separate svchost processes; fewer processes on high-RAM systems.",
       [Cmd(ps("$m=(Get-CimInstance Win32_PhysicalMemory|Measure-Object Capacity -Sum).Sum/1KB;"
               "Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control' -Name SvcHostSplitThresholdInKB -Value $m -Type DWord"),
            ps("Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control' -Name SvcHostSplitThresholdInKB -Value 3670016 -Type DWord -Force"))],
       admin=True, action=True),
    _t("disable_reserved_storage", "performance",
       "Ayrılmış depolamayı kapat", "Disable reserved storage",
       "Windows güncellemeleri için ayrılan yaklaşık 7 GB alanı serbest bırakır.",
       "Frees the roughly 7 GB Windows keeps reserved for updates.",
       [Cmd(["DISM", "/Online", "/Set-ReservedStorageState", "/State:Disabled"],
            ["DISM", "/Online", "/Set-ReservedStorageState", "/State:Enabled"])],
       admin=True, action=True, risk="medium"),
    _t("create_restore_point", "maintenance",
       "Geri yükleme noktası oluştur", "Create a restore point",
       "Değişiklik yapmadan önce sistem geri yükleme noktası oluşturur.",
       "Creates a system restore point before you make changes.",
       [Cmd(ps("Enable-ComputerRestore -Drive $env:SystemDrive -ErrorAction SilentlyContinue;"
               "Checkpoint-Computer -Description 'KeyStone' -RestorePointType MODIFY_SETTINGS"))],
       admin=True, action=True),
    _t("run_disk_cleanup", "maintenance",
       "Disk Temizleme'yi çalıştır", "Run Disk Cleanup",
       "Windows'un yerleşik disk temizleme işlemini çalıştırıp geçici dosyaları siler.",
       "Runs the built-in Windows disk cleanup and removes temporary files.",
       [Cmd(ps("cleanmgr.exe /d $env:SystemDrive /VERYLOWDISK"))],
       admin=True, action=True),
    _t("delete_temp_files", "maintenance",
       "Geçici dosyaları sil", "Delete temporary files",
       "Kullanıcı ve sistem Temp klasörlerindeki dosyaları siler (kullanımdakiler atlanır).",
       "Deletes files in the user and system Temp folders (files in use are skipped).",
       [Cmd(ps("Remove-Item \"$env:TEMP\\*\",\"$env:SystemRoot\\Temp\\*\" -Recurse -Force -ErrorAction SilentlyContinue; exit 0"))],
       admin=True, action=True),
    _t("run_mrt", "maintenance",
       "Kötü Amaçlı Yazılımları Temizleme Aracı (MRT)", "Malicious Software Removal Tool (MRT)",
       "Windows'un yerleşik zararlı yazılım temizleme aracını (MRT) başlatır; virüs ve truva atı taraması yapar.",
       "Launches the built-in Windows Malicious Software Removal Tool (MRT) to scan for and remove malware and trojans.",
       [Cmd(ps('Start-Process "$env:SystemRoot\\system32\\MRT.exe"'))],
       admin=True, action=True),
    _t("edge_debloat", "debloat",
       "Edge'i sadeleştir", "Debloat Microsoft Edge",
       "Edge'de öneriler, alışveriş yardımcısı, ödüller ve tanılama gibi gereksiz özellikleri ilkeyle kapatır.",
       "Turns off Edge recommendations, shopping assistant, rewards and diagnostics by policy.",
       [Reg("HKLM", r"SOFTWARE\Policies\Microsoft\EdgeUpdate", "CreateDesktopShortcutDefault", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "PersonalizationReportingEnabled", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "ShowRecommendationsEnabled", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "HideFirstRunExperience", 1),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "UserFeedbackAllowed", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "ConfigureDoNotTrack", 1),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "AlternateErrorPagesEnabled", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "EdgeCollectionsEnabled", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "EdgeShoppingAssistantEnabled", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "MicrosoftEdgeInsiderPromotionEnabled", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "ShowMicrosoftRewards", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "WebWidgetAllowed", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "DiagnosticData", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "EdgeAssetDeliveryServiceEnabled", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "WalletDonationEnabled", 0),
        Reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "DefaultBrowserSettingsCampaignEnabled", 0)],
       admin=True),
    _t("brave_debloat", "debloat",
       "Brave'i sadeleştir", "Debloat Brave",
       "Brave'de Rewards, Cüzdan, VPN, Yapay Zeka sohbeti, Haberler ve telemetriyi ilkeyle kapatır.",
       "Turns off Brave Rewards, Wallet, VPN, AI chat, News and telemetry by policy.",
       [Reg("HKLM", r"SOFTWARE\Policies\BraveSoftware\Brave", n, v) for n, v in [
           ("BraveRewardsDisabled", 1), ("BraveWalletDisabled", 1), ("BraveVPNDisabled", 1),
           ("BraveAIChatEnabled", 0), ("BraveStatsPingEnabled", 0), ("BraveNewsDisabled", 1),
           ("BraveTalkDisabled", 1), ("TorDisabled", 1), ("BraveP3AEnabled", 0),
           ("UrlKeyedAnonymizedDataCollectionEnabled", 0), ("SafeBrowsingExtendedReportingEnabled", 0),
           ("MetricsReportingEnabled", 0)]],
       admin=True),
    _t("disable_sync_provider_notifications", "privacy",
       "Gezgin'deki OneDrive/Microsoft 365 reklamlarını kapat", "Hide ads in File Explorer",
       "Dosya Gezgini'nde çıkan eşitleme sağlayıcısı (OneDrive, Microsoft 365) tanıtım bildirimlerini kapatır.",
       "Turns off the sync provider promotions (OneDrive, Microsoft 365) shown in File Explorer.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowSyncProviderNotifications", 0, undo=1)], recommended=True),
    _t("disable_lockscreen_tips", "privacy",
       "Kilit ekranı ipuçlarını ve reklamlarını kapat", "Turn off lock screen tips and ads",
       "Kilit ekranında eğlenceli bilgiler, ipuçları ve öneriler gösterilmesini engeller.",
       "Stops fun facts, tips and suggestions from appearing on the lock screen.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "RotatingLockScreenOverlayEnabled", 0, undo=1),
        Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338387Enabled", 0, undo=1)], recommended=True),
    _t("disable_settings_suggestions", "privacy",
       "Ayarlar uygulamasındaki önerileri kapat", "Turn off suggestions in Settings",
       "Ayarlar uygulamasında önerilen içerik ve tanıtımları gizler.",
       "Hides suggested content and promotions inside the Settings app.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338393Enabled", 0, undo=1),
        Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-353694Enabled", 0, undo=1),
        Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-353696Enabled", 0, undo=1)], recommended=True),
    _t("disable_windows_tips", "privacy",
       "Windows ipuçları ve önerilerini kapat", "Turn off Windows tips and suggestions",
       "Windows kullanırken çıkan ipucu, püf noktası ve öneri bildirimlerini kapatır.",
       "Turns off the tips, tricks and suggestion notifications shown while you use Windows.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338389Enabled", 0, undo=1)], recommended=True),
    _t("disable_finish_setup_nag", "privacy",
       "'Cihazı kurmayı bitir' önerilerini kapat", "Turn off 'finish setting up your device' nags",
       "Windows'tan en iyi şekilde yararlanmak için kurulumu tamamlama önerilerini gizler.",
       "Hides the prompts that suggest ways to finish setting up this device.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\UserProfileEngagement", "ScoobeSystemSettingEnabled", 0, undo=1)], recommended=True),
    _t("disable_welcome_experience", "privacy",
       "Güncelleme sonrası karşılama ekranını kapat", "Turn off the post-update welcome screen",
       "Güncellemelerden sonra ve oturum açarken çıkan 'neler yeni' karşılama deneyimini kapatır.",
       "Turns off the 'what's new' welcome experience shown after updates and at sign-in.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-310093Enabled", 0, undo=1)], recommended=True),
    _t("disable_tailored_diagnostic", "privacy",
       "Tanılama verisiyle kişiselleştirmeyi kapat", "Turn off diagnostic-data personalisation",
       "Tanılama verilerinin kişiselleştirilmiş deneyimler için kullanılmasını engeller.",
       "Stops diagnostic data from being used to tailor experiences to you.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Privacy", "TailoredExperiencesWithDiagnosticDataEnabled", 0, undo=1)], recommended=True),
    _t("disable_start_recommendations_iris", "interface",
       "Başlat menüsü öneri ve reklamlarını kapat", "Turn off Start menu tips and promoted apps",
       "Başlat'ta ipuçları, kısayollar ve yeni uygulama önerilerini gösteren bölümü kapatır.",
       "Turns off the Start section that shows tips, shortcuts and new app suggestions.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_IrisRecommendations", 0, undo=1)], restart="explorer", recommended=True),
    _t("disable_notification_smart_optout", "interface",
       "'Bildirimleri kapatalım mı?' önerisini kapat", "Turn off the 'turn off notifications?' prompt",
       "Uzun süredir açılmayan uygulamaların bildirimleri için çıkan öneri penceresini kapatır.",
       "Turns off the prompt that offers to silence notifications from apps you rarely open.",
       [Reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings\Windows.ActionCenter.SmartOptOut", "Enabled", 0, undo=1)]),
    _t("disable_edge_search_widget", "privacy",
       "Edge masaüstü arama çubuğunu kapat", "Disable the Edge desktop search bar",
       "Edge'in masaüstünde gösterdiği arama widget çubuğunu ilkeyle kapatır.",
       "Turns off the Edge desktop search widget bar by policy.",
       [Reg("HKCU", r"Software\Policies\Microsoft\Edge", "WebWidgetAllowed", 0, undo=1)]),
]


WARNINGS = {
    "disable_uac_prompts": ("high",
        "Güvenliği ciddi şekilde düşürür: programlar yönetici yetkisini sormadan yükselebilir. Yalnızca ne yaptığınızı biliyorsanız açın.",
        "Seriously lowers security: programs can gain admin rights without asking. Only enable it if you know why."),
    "remove_onedrive": ("high",
        "Yalnızca bulutta duran dosyalar bu bilgisayarda açılamaz olur. Önce önemli dosyaları indirin; Masaüstü/Belgeler OneDrive'a taşınmışsa dosyalarınızı kontrol edin.",
        "Files that exist only in the cloud stop being available. Download what you need first, and check Desktop/Documents if OneDrive backup was on."),
    "disable_ipv6": ("medium",
        "Bazı ağ, VPN, Xbox ve ev ağı özellikleri IPv6 gerektirir; internet sorunu yaşarsanız geri alın.",
        "Some networks, VPNs, Xbox and home-network features need IPv6; revert it if you run into connection problems."),
    "disable_reserved_storage": ("medium",
        "Disk neredeyse doluyken Windows güncellemeleri başarısız olabilir. Yalnızca yeterli boş alanınız varsa kullanın.",
        "Windows updates can fail when the disk is nearly full. Only use it if you have enough free space."),
    "disable_svchost_splitting": ("medium",
        "Tek bir hizmetin çökmesi aynı işlemdeki diğer hizmetleri de düşürebilir. Yalnızca bol RAM'iniz varsa (16 GB+) anlamlıdır; yeniden başlatma gerekir.",
        "One crashing service can take down the others sharing its process. Only worth it with plenty of RAM (16 GB+); a restart is needed."),
    "disable_wpbt": ("medium",
        "Bazı üreticilerin (Lenovo, ASUS, HP vb.) bellenimden gelen otomatik yardımcı yazılımları çalışmaz; çalınma koruması (Computrace) gibi özellikler devre dışı kalır.",
        "Vendor helper software pushed from firmware (Lenovo, ASUS, HP...) stops running, and anti-theft features such as Computrace are disabled."),
    "block_oem_driver_autoinstall": ("medium",
        "Windows'un sürücü aramasını da kapatır: yeni takılan aygıtların sürücüleri otomatik gelmez, elle kurmanız gerekir.",
        "Also turns off Windows driver search: drivers for newly plugged devices will not arrive automatically."),
    "block_device_metadata": ("medium",
        "Yazıcı ve çevre birimleri için üretici uygulamaları ve ayrıntılı aygıt simgeleri otomatik gelmez.",
        "Vendor apps and detailed device icons for printers and peripherals will no longer arrive automatically."),
    "disable_location": ("medium",
        "Haritalar, hava durumu, 'Cihazımı bul' ve saat dilimi otomatik ayarı çalışmaz. Konum isteyen uygulamalar hata verebilir.",
        "Maps, weather, Find My Device and automatic time zone stop working. Apps that ask for location may show errors."),
    "disable_hibernation": ("medium",
        "Hazırda bekletme ve Hızlı Başlangıç kullanılamaz; dizüstü bilgisayarda pil bitince açık işleriniz kaybolabilir.",
        "Hibernate and Fast Startup become unavailable; on a laptop, open work can be lost when the battery runs out."),
    "realtime_clock_utc": ("medium",
        "Yalnızca Linux ile çift önyükleme yapıyorsanız anlamlıdır. Linux tarafı da UTC'ye ayarlanmazsa saat, saat dilimi farkı kadar kayar.",
        "Only useful when dual-booting with Linux. If the Linux side is not set to UTC too, the clock will be off by your time-zone offset."),
    "disable_rdp_unsigned_warning": ("medium",
        "Kötü amaçlı bir .rdp dosyası uyarı çıkmadan bağlantı kurabilir. Yalnızca güvendiğiniz dosyaları açın.",
        "A malicious .rdp file could connect without any warning. Only open files you trust."),
    "developer_mode": ("medium",
        "İmzasız paketlerin yüklenmesine izin verir; güvenmediğiniz yazılımları kurmayın.",
        "Allows sideloading unsigned packages; do not install software you do not trust."),
    "disable_notification_center": ("medium",
        "Hiçbir uygulamanın bildirimi görünmez (alarm, takvim, mesajlar dahil) ve bildirim paneli açılmaz.",
        "No app notifications will show (alarms, calendar and messages included) and the notification panel will not open."),
    "disable_background_apps": ("medium",
        "Mail, Takvim ve mesajlaşma gibi Store uygulamaları kapalıyken bildirim almaz ve eşitlenmez.",
        "Store apps such as Mail, Calendar and messaging stop syncing and notifying while closed."),
    "delete_temp_files": ("medium",
        "Temp klasörlerindeki dosyaları kalıcı olarak siler; yalnızca Temp'te duran belgeler kaybolabilir. Önce açık programları kapatın.",
        "Permanently deletes files in the Temp folders; documents that live only in Temp can be lost. Close your programs first."),
    "disable_telemetry": ("low",
        "Windows Insider programı ve bazı Microsoft geri bildirim özellikleri çalışmaz. Windows Update etkilenmez.",
        "The Windows Insider programme and some Microsoft feedback features stop working. Windows Update is not affected."),
    "disable_windows_tips": ("low",
        "Yeni özelliklerden haberdar eden ipucu bildirimleri de kesilir.",
        "Tip notifications that tell you about new features are cut as well."),
    "fast_reboot": ("low",
        "Yanıt vermeyen uygulamalar 2 sn sonra kapatılır; o uygulamadaki kaydedilmemiş işler kaybolur.",
        "Hung apps are closed after 2 s; unsaved work in them is lost."),
    "edge_debloat": ("low",
        "Edge'de 'kuruluşunuz tarafından yönetiliyor' ibaresi görünür ve ilkeyle kontrol edilen ayarlar arayüzden değiştirilemez.",
        "Edge shows 'managed by your organisation' and the policy-controlled settings cannot be changed in its UI."),
    "brave_debloat": ("low",
        "Brave'de 'kuruluşunuz tarafından yönetiliyor' ibaresi görünür; Rewards, Cüzdan ve VPN kullanılamaz.",
        "Brave shows 'managed by your organisation' and Rewards, Wallet and VPN become unavailable."),
    "start_menu_old_layout": ("low",
        "Windows sürümüne bağlıdır; yeni yapılarda etkisiz kalabilir.",
        "Depends on the Windows build and may do nothing on newer ones."),
    "disable_lock_screen": ("low",
        "Bazı Windows 11 yapıları bu ilkeyi yok sayar.",
        "Some Windows 11 builds ignore this policy."),
    "run_disk_cleanup": ("low",
        "Seçilen kategorilerdeki dosyalar (geri dönüşüm kutusu dahil) kalıcı olarak silinir.",
        "Files in the selected categories (Recycle Bin included) are permanently deleted."),
    "lock_screen_timeout_unhide": ("low",
        "Ayar eklendikten sonra Denetim Masası > Güç Seçenekleri > Plan ayarlarını değiştir > Gelişmiş güç ayarlarını değiştir > Ekran menüsünden süreyi dilediğiniz gibi seçebilirsiniz.",
        "After unhiding, open Control Panel > Power Options > Change plan settings > Change advanced power settings > Display to select any timeout."),
    "wsl2": ("low",
        "WSL ve Sanal Makine Platformunun tam olarak devreye girmesi için bilgisayarınızı yeniden başlatmanız gerekebilir.",
        "A system restart may be required for WSL and Virtual Machine Platform to take full effect."),
    "virtual_machine_platform": ("low",
        "Sanal Makine Platformunun tam olarak devreye girmesi için bilgisayarınızı yeniden başlatmanız gerekebilir.",
        "A system restart may be required for Virtual Machine Platform to take full effect."),
    "hyper_v": ("low",
        "Hyper-V bileşenlerinin tam olarak devreye girmesi için bilgisayarınızı yeniden başlatmanız gerekebilir.",
        "A system restart may be required for Hyper-V to take full effect."),
    "windows_sandbox": ("low",
        "Windows Sandbox, BIOS/UEFI üzerinde donanım sanallaştırmasının (VT-x / AMD-V) açık olmasını gerektirir.",
        "Windows Sandbox requires hardware virtualization (VT-x / AMD-V) enabled in BIOS/UEFI."),
    "windows_hypervisor_platform": ("low",
        "Windows Hipervizör Platformunun devreye girmesi için bilgisayarınızı yeniden başlatmanız gerekebilir.",
        "A system restart may be required for Windows Hypervisor Platform to take full effect."),
    "reboot_to_bios_script": ("low",
        "İndirilen .bat dosyası çift tıklandığında bilgisayarınızı hemen yeniden başlatır. Dosyayı çalıştırmadan önce açık çalışmalarınızı kaydedin.",
        "When double-clicked, the downloaded .bat file immediately restarts your computer. Save your open work before running it."),
    "run_mrt": ("low",
        "Windows'un resmi Kötü Amaçlı Yazılımları Temizleme Aracı'nı (mrt.exe) açar. Açılan pencereden Hızlı veya Tam Tarama seçebilirsiniz.",
        "Opens Microsoft's official Malicious Software Removal Tool (mrt.exe). You can select Quick Scan or Full Scan in the wizard."),
}
annotate(TWEAKS, WARNINGS)


def restart_shell(which: str) -> None:
    if which == "explorer":
        proc.run(ps("Stop-Process -Name explorer -Force; Start-Process explorer.exe"), timeout=30)
