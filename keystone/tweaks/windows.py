"""Windows tweaks (registry, powercfg, shell verbs). Ported from KeyStone 2.x."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

from ..core import proc
from .engine import DELETE, Backends, Cmd, Op, Reg, RegKey, Tweak, _ok, ps

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
       [Reg("HKCU", r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions", 1)],
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
    _t("clear_icon_cache", "maintenance",
       "Simge önbelleğini yenile", "Rebuild icon cache",
       "Bozuk ya da beyaz görünen simgeleri düzeltmek için IconCache.db'yi sıfırlar.",
       "Resets IconCache.db to fix broken or blank icons.",
       [Cmd(_clear_icon_cache())], action=True),
]


def restart_shell(which: str) -> None:
    if which == "explorer":
        proc.run(ps("Stop-Process -Name explorer -Force; Start-Process explorer.exe"), timeout=30)
