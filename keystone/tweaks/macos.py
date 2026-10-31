"""macOS tweaks via ``defaults`` and a few system commands."""
from __future__ import annotations

from ..core import proc
from .engine import Cmd, Defaults, Tweak

M = "macos"
G = "NSGlobalDomain"


def _t(id, cat, tr, en, dtr, den, ops, **kw) -> Tweak:
    return Tweak(id, M, cat, {"tr": tr, "en": en}, {"tr": dtr, "en": den}, ops, **kw)


def _shot_dir_probe(b) -> bool:
    r = b.run(["defaults", "read", "com.apple.screencapture", "location"])
    return r.ok and r.out.strip().rstrip("/").endswith("Pictures/Screenshots")


TWEAKS: list[Tweak] = [
    _t("mac_show_extensions", "interface", "Dosya uzantılarını göster", "Show file extensions",
       "Finder'da tüm dosya uzantılarını gösterir.", "Show every file extension in Finder.",
       [Defaults(G, "AppleShowAllExtensions", "bool", True)], restart="Finder", recommended=True),
    _t("mac_show_hidden", "interface", "Gizli dosyaları göster", "Show hidden files",
       "Finder'da nokta ile başlayan dosyaları gösterir (Cmd+Shift+. ile de açılır).",
       "Show dotfiles in Finder (same as Cmd+Shift+.).",
       [Defaults("com.apple.finder", "AppleShowAllFiles", "bool", True)], restart="Finder"),
    _t("mac_path_bar", "interface", "Yol ve durum çubuğu", "Path and status bar",
       "Finder penceresinin altında klasör yolunu ve boş alanı gösterir.",
       "Show the folder path and free space at the bottom of Finder windows.",
       [Defaults("com.apple.finder", "ShowPathbar", "bool", True),
        Defaults("com.apple.finder", "ShowStatusBar", "bool", True)], restart="Finder", recommended=True),
    _t("mac_folders_first", "interface", "Klasörler önce", "Folders first",
       "Finder'da sıralarken klasörleri dosyaların üstünde tutar.",
       "Keep folders above files when sorting in Finder.",
       [Defaults("com.apple.finder", "_FXSortFoldersFirst", "bool", True)], restart="Finder", recommended=True),
    _t("mac_no_ds_store", "performance", "Ağ ve USB'de .DS_Store yazma", "No .DS_Store on network/USB",
       "Paylaşılan klasörlere ve USB belleklere .DS_Store dosyası bırakmaz.",
       "Stop littering network shares and USB drives with .DS_Store files.",
       [Defaults("com.apple.desktopservices", "DSDontWriteNetworkStores", "bool", True),
        Defaults("com.apple.desktopservices", "DSDontWriteUSBStores", "bool", True)], recommended=True),
    _t("mac_dock_autohide_fast", "interface", "Dock'u bekletmeden gizle", "Instant Dock auto-hide",
       "Dock otomatik gizlenir ve fare yaklaşınca gecikmeden açılır.",
       "Auto-hide the Dock and show it with no delay.",
       [Defaults("com.apple.dock", "autohide", "bool", True),
        Defaults("com.apple.dock", "autohide-delay", "float", 0)], restart="Dock"),
    _t("mac_dock_no_recents", "interface", "Dock'ta son uygulamaları gizle", "No recent apps in Dock",
       "Dock'ta 'Son kullanılan uygulamalar' bölümünü kapatır.", "Remove the recent-apps section from the Dock.",
       [Defaults("com.apple.dock", "show-recents", "bool", False)], restart="Dock", recommended=True),
    _t("mac_fast_key_repeat", "performance", "Hızlı tuş tekrarı", "Fast key repeat",
       "Basılı tutulan tuşun daha erken ve daha hızlı tekrar etmesini sağlar (yeniden giriş gerekir).",
       "Keys repeat sooner and faster when held (takes effect after re-login).",
       [Defaults(G, "KeyRepeat", "int", 2), Defaults(G, "InitialKeyRepeat", "int", 15),
        Defaults(G, "ApplePressAndHoldEnabled", "bool", False)]),
    _t("mac_tap_to_click", "interface", "Dokunarak tıkla", "Tap to click",
       "Trackpad'e hafifçe dokunmak tıklama sayılır.", "A light tap on the trackpad counts as a click.",
       [Defaults("com.apple.AppleMultitouchTrackpad", "Clicking", "bool", True),
        Defaults("com.apple.driver.AppleBluetoothMultitouch.trackpad", "Clicking", "bool", True)], recommended=True),
    _t("mac_no_autocorrect", "developer", "Otomatik düzeltmeyi kapat", "Disable autocorrect",
       "Yazım düzeltme, akıllı tırnak ve tire değiştirmelerini kapatır (kod yazarken faydalı).",
       "Turns off autocorrect, smart quotes and smart dashes — handy when writing code.",
       [Defaults(G, "NSAutomaticSpellingCorrectionEnabled", "bool", False),
        Defaults(G, "NSAutomaticQuoteSubstitutionEnabled", "bool", False),
        Defaults(G, "NSAutomaticDashSubstitutionEnabled", "bool", False)]),
    _t("mac_expand_save", "interface", "Kaydet penceresini genişlet", "Expanded save dialogs",
       "Kaydet ve Yazdır pencereleri varsayılan olarak tam görünümde açılır.",
       "Save and Print dialogs open expanded by default.",
       [Defaults(G, "NSNavPanelExpandedStateForSaveMode", "bool", True),
        Defaults(G, "PMPrintingExpandedStateForPrint", "bool", True)]),
    _t("mac_screenshot_folder", "interface", "Ekran görüntüleri klasörü", "Screenshots folder",
       "Ekran görüntülerini masaüstü yerine ~/Pictures/Screenshots klasörüne kaydeder.",
       "Save screenshots to ~/Pictures/Screenshots instead of the Desktop.",
       [Cmd(["sh", "-c", 'mkdir -p "$HOME/Pictures/Screenshots" && defaults write com.apple.screencapture location "$HOME/Pictures/Screenshots"'],
            ["defaults", "delete", "com.apple.screencapture", "location"], probe=_shot_dir_probe)],
       restart="SystemUIServer", recommended=True),
    _t("mac_screenshot_no_shadow", "interface", "Ekran görüntüsünde gölge yok", "No window shadow in screenshots",
       "Pencere ekran görüntülerinde kenar gölgesini kaldırır.", "Drop the shadow around window screenshots.",
       [Defaults("com.apple.screencapture", "disable-shadow", "bool", True)], restart="SystemUIServer"),
    _t("mac_flush_dns", "maintenance", "DNS önbelleğini temizle", "Flush DNS cache",
       "Ad çözümleme sorunları için DNS önbelleğini sıfırlar.", "Reset the DNS cache when names resolve wrongly.",
       [Cmd(["sh", "-c", "dscacheutil -flushcache; killall -HUP mDNSResponder"], root=True)], action=True, admin=True),
    _t("mac_rebuild_launchservices", "maintenance", "'Birlikte aç' menüsünü onar", "Repair 'Open With' menu",
       "Yinelenen uygulamalarla dolan 'Birlikte aç' listesini yeniden oluşturur.",
       "Rebuilds the Launch Services database behind a cluttered 'Open With' menu.",
       [Cmd(["/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister",
             "-kill", "-r", "-domain", "local", "-domain", "system", "-domain", "user"])], action=True),
]


def restart_shell(which: str) -> None:
    if which:
        proc.run(["killall", which], timeout=15)
