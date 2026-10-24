"""
Keystone Localization (i18n) Engine
Provides bilingual support (Turkish & English) for all UI components,
system tweaks, backup items, categories, and dialogs.
"""

from typing import Optional, Tuple, Dict, Any

_CURRENT_LANG: str = "tr"

STRINGS: Dict[str, Dict[str, str]] = {
    "tr": {
        # App & Window
        "app_window_title": "KeyStone",
        "app_title": "KEYSTONE SETUP v1.0",
        "app_subtitle": "Windows Format Sonrası Gerekli Kütüphaneler, Yazılımcı Araçları ve Kayıt Defteri İnce Ayarları",
        "admin_elevated": "[YÖNETİCİ: AKTİF]",
        "admin_run_as": "Yönetici Olarak Çalıştır",
        "admin_tooltip": "DirectX, Visual C++ ve Sistem Regedit ayarları için yönetici haklarıyla başlatın.",
        "profile_prefix": "Profil: ",
        "settings_btn": "Ayarlar",
        "settings_btn_tooltip": "Ayarlar & Tercihler (Ctrl+,)",

        # Sidebar Drawer & Rail
        "tabs_title": "SEKMELER",
        "collapse_tabs": " Daralt",
        "collapse_tooltip": "Sekmeler Panelini Daralt (Ctrl+B)",
        "expand_tooltip": "Sekmeleri Genişlet (Ctrl+B)",
        "tab_apps": "  Yazılım & Programlar",
        "tab_tweaks": "  Regedit & İnce Ayar",
        "tab_backup": "  Yedekleme & Geri Yükle",
        "tab_apps_rail_tip": "Yazılım & Programlar",
        "tab_tweaks_rail_tip": "Regedit / İnce Ayarlar",
        "tab_backup_rail_tip": "Yedekleme & Geri Yükle",

        # Top Intel HUD Bar
        "hud_info_panel": "BİLGİ PANELİ",
        "hud_app_badge": "PROGRAM BİLGİSİ",
        "hud_tweak_badge": "REGEDIT AYARI",
        "hud_backup_badge": "YEDEK & RESTORE",
        "hud_transfer_cat": "AYAR TRANSFERİ",
        "hud_package_id": "Paket ID",
        "hud_setting_key": "Ayar",
        "hud_module": "Modül",
        "hud_hint_website": "[Sağ Tık: Resmi Site]",
        "hud_hint_registry": "[Kayıt Defteri]",
        "hud_hint_backup": "[Format Öncesi/Sonrası]",
        "hud_web_title": "RESMİ WEB SİTESİ",
        "hud_web_opened": "[Tarayıcıda Açıldı]",
        "hud_web_cat": "[WEB TARAYICI]",
        "hud_category": "Kategori:",
        "hud_size": "Boyut:",
        "hud_recommended": "Önerilen:",
        "hud_status": "Durum:",
        "hud_website": "Resmi Web Sitesi:",
        "hud_open_site": "Web Sitesine Git",
        "hud_yes": "Evet",
        "hud_no": "Hayır",
        "hud_installed": "Kurulu",
        "hud_not_installed": "Kurulu Değil",
        "hud_active": "Aktif",
        "hud_inactive": "Kapalı / Varsayılan",
        "hud_available": "Sistemde Mevcut",
        "hud_not_found": "Bulunamadı",
        "hud_has_backup": "Yedek Klasöründe Mevcut",
        "hud_no_backup": "Yedek Bulunamadı",

        # Search & Presets Bar
        "search_apps_placeholder": "Program ara... (Ctrl+F)",
        "search_tweaks_placeholder": "Kayıt defteri ayarı ara... (Ctrl+F)",
        "search_backup_placeholder": "Yedekleme veya geri yükleme öğesi ara... (Ctrl+F)",
        "presets_label": "Hızlı Seçim:",
        "preset_select_prompt": "-- Hazır Paket Seçin --",
        "preset_essential": "Temel & Günlük Programlar",
        "preset_dev": "Yazılımcı & Geliştirici",
        "preset_database": "Veritabanı & Yönetim",
        "preset_gamer": "Oyuncu & Gaming",
        "preset_ai": "Yapay Zeka & Veri",
        "preset_hardware": "Donanım & Test Araçları",
        "btn_apply_preset": "Paketi Uygula",
        "btn_apply_preset_tip": "Seçili hazır paketteki uygulamaları listeye seçer",
        "select_all": "Tümünü Seç",
        "clear_selection": "Temizle",
        "select_recommended_tweaks": "Önerilen Ayarları Seç",
        "select_active_tweaks": "Kurulu Olanları Seç",
        "deselect_active_tweaks": "Kurulu Seçimini Kaldır",
        "btn_restart_explorer": "Dosya Gezginini Yeniden Başlat",
        "btn_restart_explorer_tip": "Sağ tık ve görünüm ayarlarının anında uygulanması için Explorer'ı yeniden başlatır.",
        "btn_clear_icon_cache": "İkon Önbelleğini Temizle",
        "category_label": "Kategori:",

        # Backup Page Controls
        "operation_label": "İşlem:",
        "op_backup": "Yedek Al (Format Öncesi)",
        "op_restore": "Geri Yükle (Format Sonrası)",
        "target_dir_label": "Hedef Klasör:",
        "btn_browse": "Gözat...",
        "btn_open_folder": "Klasörü Aç",

        # Action Bar & Counter
        "console_log": "Konsol Günlüğü",
        "console_hide": "Konsolu Gizle",
        "cancel_btn": "İptal Et",
        "download_setups_btn": "Setup Dosyalarını İndir",
        "download_setups_tip": "Seçilen programların kurulum (.exe / .msi) dosyalarını bir klasöre kaydeder.",
        "revert_tweaks_btn": "Seçilen Ayarları Kaldır (Varsayılan)",
        "revert_tweaks_tip": "Seçili kayıt defteri ayarlarını kaldırıp orijinal Windows varsayılanlarına döndürür.",
        "btn_install": "Seçilenleri Kur",
        "btn_apply_tweaks": "Seçilen Ayarları Uygula",
        "btn_start_backup": "Seçilenleri Klasöre Yedekle",
        "btn_start_restore": "Yedekten Sisteme Geri Yükle",
        "btn_settings_active": "Ayarlar Aktif",
        "selected_label": "Seçilen",
        "programs_unit": "Program",
        "tweaks_unit": "Ayar",
        "backup_unit": "Ayar Öğesi",
        "active_label": "Aktif",
        "settings_counter_label": "Görünüm, Dil ve Profil Ayarları",
        "counter_apps": "{count} program seçildi",
        "counter_tweaks": "{count} ince ayar seçildi",
        "counter_backup": "{count} yedek öğesi seçildi",

        # Card Badges
        "card_portable": "Portable",
        "card_setup": "Setup",
        "card_portable_tip": "Taşınabilir Sürüm (Kurulumsuz)",
        "card_setup_tip": "Kurulum Sürümü (Sisteme Yüklenir)",
        "card_status_installed": "Kurulu",
        "card_status_waiting": "Bekliyor",
        "card_status_downloaded": "İndirildi",
        "card_status_completed": "Tamamlandı",
        "card_status_error": "Hata",
        "tweak_status_active": "[Aktif]",
        "tweak_status_inactive": "[Kapalı]",
        "backup_status_available": "[Mevcut]",
        "backup_status_not_found": "[Bulunamadı]",
        "backup_status_has_backup": "[Yedek Var]",
        "backup_status_no_backup": "[Yedek Yok]",

        # Settings Page
        "settings_header_title": "Ayarlar",
        "settings_header_desc": "•  Görünüm modu, dil ve profil tercihleri",
        "settings_lang_title": "Dil Tercihi / Language",
        "settings_lang_desc": "Uygulama arayüz dilini Türkçe veya İngilizce olarak değiştirin.",
        "lang_tr": "Türkçe",
        "lang_en": "English",
        "settings_theme_title": "Görünüm & Renk Teması",
        "settings_theme_desc": "Uygulamanın renk modunu gece (karanlık) veya gündüz (aydınlık) olarak değiştirin.",
        "theme_dark": "Karanlık Mod",
        "theme_light": "Aydınlık Mod",
        "settings_prof_title": "Çalışma Profili Yönetimi",
        "settings_prof_desc": "Farklı kurulum senaryoları için bağımsız profiller oluşturun ve seçimlerinizi ayrı ayrı saklayın.",
        "active_profile_label": "Aktif Profil:",
        "btn_new_profile": "+ Yeni Profil",
        "btn_new_profile_tip": "Sıfırdan bağımsız yeni bir profil oluşturur",
        "btn_rename_profile": "Yeniden Adlandır",
        "btn_rename_profile_tip": "Seçili profilin ismini değiştirir",
        "btn_delete_profile": "Profili Sil",
        "btn_delete_profile_tip": "Seçili profili kalıcı olarak siler",
        "profile_stats_template": "Bu Profilde Kayıtlı: {apps} Program  •  {tweaks} İnce Ayar  •  {backups} Yedek Öğesi",
        "settings_sys_title": "Yönetici Hakları (Admin Elevation)",
        "settings_sys_desc": "Windows Regedit ayarlarının uygulanabilmesi ve yazılım kurulumları için gereklidir.",
        "admin_status_active": "Yönetici Yetkisi: Aktif",
        "btn_restart_admin": "Yönetici Olarak Yeniden Başlat",
        "settings_about_title": "Keystone  •  Sürüm 2.0 (Portable)",

        # Dialogs & Prompts
        "msg_warning": "Uyarı",
        "msg_info": "Bilgi",
        "msg_success": "İşlem Tamamlandı",
        "msg_error": "Hata",
        "dialog_new_profile_title": "Yeni Profil Ekle — Sıfırdan Başla",
        "dialog_new_profile_header": "YENİ KULLANICI PROFİLİ",
        "dialog_new_profile_info1": "Tıpkı tarayıcılardaki gibi bu profil tamamen SIFIRDAN başlar.",
        "dialog_new_profile_info2": "Seçeceğiniz programlar, Windows ayarları ve yedekler bu profile özel olarak anında otomatik kaydedilir.",
        "dialog_profile_name_lbl": "Profil Adı:",
        "dialog_profile_placeholder": "Örn: Oyun Bilgisayarı, İş & Yazılım, Format 2026...",
        "dialog_btn_create_profile": "Profili Oluştur (Sıfırdan Başla)",
        "dialog_btn_cancel": "İptal",
        "dialog_btn_save": "Kaydet",
        "dialog_rename_title": "Profili Yeniden Adlandır",
        "dialog_rename_lbl": "Yeni Profil Adı:",
        "dialog_name_empty_warning": "Lütfen geçerli bir profil adı girin!",
        "dialog_confirm_delete_profile": "'{name}' profilini silmek istediğinize emin misiniz?\nBu profile ait tüm seçimler kalıcı olarak silinecektir.",
        "dialog_cannot_delete_last_profile": "Son kalan varsayılan profili silemezsiniz.",
        "dialog_select_backup_dir": "Yedeklerin Kaydedileceği Hedef Klasörü Seçin",
        "dialog_select_restore_dir": "Yedeklerin Bulunduğu Klasörü Seçin",
        "dialog_no_selection_warning": "Lütfen işlem yapmak için en az bir öğe seçin!",
        "dialog_dir_not_found": "Seçilen klasör mevcut değil veya erişilemiyor.",
        "dialog_tweaks_applied_msg": "Seçilen kayıt defteri ayarları başarıyla uygulandı.",
        "dialog_tweaks_reverted_msg": "Seçilen ayarlar varsayılan Windows ayarlarına geri döndürüldü."
    },
    "en": {
        # App & Window
        "app_window_title": "KeyStone",
        "app_title": "KEYSTONE SETUP v1.0",
        "app_subtitle": "Windows Post-Installation Runtimes, Developer Tools & Registry Optimizations",
        "admin_elevated": "[ADMIN: ELEVATED]",
        "admin_run_as": "Run as Administrator",
        "admin_tooltip": "Launch with administrator privileges for DirectX, Visual C++, and system registry tweaks.",
        "profile_prefix": "Profile: ",
        "settings_btn": "Settings",
        "settings_btn_tooltip": "Settings & Preferences (Ctrl+,)",

        # Sidebar Drawer & Rail
        "tabs_title": "TABS",
        "collapse_tabs": " Collapse",
        "collapse_tooltip": "Collapse Navigation Tabs (Ctrl+B)",
        "expand_tooltip": "Expand Navigation Tabs (Ctrl+B)",
        "tab_apps": "  Software & Apps",
        "tab_tweaks": "  Registry & Tweaks",
        "tab_backup": "  Backup & Restore",
        "tab_apps_rail_tip": "Software & Apps",
        "tab_tweaks_rail_tip": "Registry / Tweaks",
        "tab_backup_rail_tip": "Backup & Restore",

        # Top Intel HUD Bar
        "hud_info_panel": "INFO PANEL",
        "hud_app_badge": "APPLICATION INFO",
        "hud_tweak_badge": "REGEDIT TWEAK",
        "hud_backup_badge": "BACKUP & RESTORE",
        "hud_transfer_cat": "SETTING TRANSFER",
        "hud_package_id": "Package ID",
        "hud_setting_key": "Setting",
        "hud_module": "Module",
        "hud_hint_website": "[Right Click: Official Site]",
        "hud_hint_registry": "[Registry]",
        "hud_hint_backup": "[Pre/Post Format]",
        "hud_web_title": "OFFICIAL WEBSITE",
        "hud_web_opened": "[Opened in Browser]",
        "hud_web_cat": "[WEB BROWSER]",
        "hud_category": "Category:",
        "hud_size": "Size:",
        "hud_recommended": "Recommended:",
        "hud_status": "Status:",
        "hud_website": "Official Website:",
        "hud_open_site": "Visit Website",
        "hud_yes": "Yes",
        "hud_no": "No",
        "hud_installed": "Installed",
        "hud_not_installed": "Not Installed",
        "hud_active": "Active",
        "hud_inactive": "Disabled / Default",
        "hud_available": "Available on System",
        "hud_not_found": "Not Found",
        "hud_has_backup": "Found in Backup Folder",
        "hud_no_backup": "No Backup Found",

        # Search & Presets Bar
        "search_apps_placeholder": "Search software... (Ctrl+F)",
        "search_tweaks_placeholder": "Search registry tweaks... (Ctrl+F)",
        "search_backup_placeholder": "Search backup items... (Ctrl+F)",
        "presets_label": "Presets:",
        "preset_select_prompt": "-- Select Preset Bundle --",
        "preset_essential": "Essential & Daily Apps",
        "preset_dev": "Developer & Coding",
        "preset_database": "Database Management",
        "preset_gamer": "Gaming & Emulators",
        "preset_ai": "AI & Data Science",
        "preset_hardware": "Hardware & Benchmark",
        "btn_apply_preset": "Apply Preset",
        "btn_apply_preset_tip": "Selects applications from the chosen preset bundle",
        "select_all": "Select All",
        "clear_selection": "Clear",
        "select_recommended_tweaks": "Select Recommended",
        "select_active_tweaks": "Select Active Tweaks",
        "deselect_active_tweaks": "Deselect Active",
        "btn_restart_explorer": "Restart File Explorer",
        "btn_restart_explorer_tip": "Restarts Windows Explorer to activate shell and context menu tweaks immediately.",
        "btn_clear_icon_cache": "Clear Icon Cache",
        "category_label": "Category:",

        # Backup Page Controls
        "operation_label": "Operation:",
        "op_backup": "Backup (Pre-Format)",
        "op_restore": "Restore (Post-Format)",
        "target_dir_label": "Target Directory:",
        "btn_browse": "Browse...",
        "btn_open_folder": "Open Folder",

        # Action Bar & Counter
        "console_log": "Console Log",
        "console_hide": "Hide Console",
        "cancel_btn": "Cancel",
        "download_setups_btn": "Download Setup Files",
        "download_setups_tip": "Downloads installer (.exe / .msi) files of selected applications to a local directory.",
        "revert_tweaks_btn": "Revert Selected Tweaks (Default)",
        "revert_tweaks_tip": "Removes selected registry tweaks and restores original Windows defaults.",
        "btn_install": "Install Selected",
        "btn_apply_tweaks": "Apply Selected Tweaks",
        "btn_start_backup": "Backup Selected to Folder",
        "btn_start_restore": "Restore Selected from Backup",
        "btn_settings_active": "Settings Active",
        "selected_label": "Selected",
        "programs_unit": "Apps",
        "tweaks_unit": "Tweaks",
        "backup_unit": "Backup Items",
        "active_label": "Active",
        "settings_counter_label": "Appearance, Language & Profile Settings",
        "counter_apps": "{count} software selected",
        "counter_tweaks": "{count} tweaks selected",
        "counter_backup": "{count} backup items selected",

        # Card Badges
        "card_portable": "Portable",
        "card_setup": "Setup",
        "card_portable_tip": "Portable Version (No installation required)",
        "card_setup_tip": "Installer Version (Installs to system)",
        "card_status_installed": "Installed",
        "card_status_waiting": "Pending",
        "card_status_downloaded": "Downloaded",
        "card_status_completed": "Completed",
        "card_status_error": "Error",
        "tweak_status_active": "[Active]",
        "tweak_status_inactive": "[Disabled]",
        "backup_status_available": "[Available]",
        "backup_status_not_found": "[Not Found]",
        "backup_status_has_backup": "[Backup Exists]",
        "backup_status_no_backup": "[No Backup]",

        # Settings Page
        "settings_header_title": "Settings",
        "settings_header_desc": "•  Appearance mode, language, and profile preferences",
        "settings_lang_title": "Language / Dil Tercihi",
        "settings_lang_desc": "Select the application interface language (Turkish or English).",
        "lang_tr": "Türkçe",
        "lang_en": "English",
        "settings_theme_title": "Appearance & Color Theme",
        "settings_theme_desc": "Switch the application color scheme between dark and light themes.",
        "theme_dark": "Dark Mode",
        "theme_light": "Light Mode",
        "settings_prof_title": "Workspace Profile Management",
        "settings_prof_desc": "Create isolated profiles for different installation scenarios and store your preferences separately.",
        "active_profile_label": "Active Profile:",
        "btn_new_profile": "+ New Profile",
        "btn_new_profile_tip": "Creates a brand new isolated profile from scratch",
        "btn_rename_profile": "Rename",
        "btn_rename_profile_tip": "Renames the selected profile",
        "btn_delete_profile": "Delete Profile",
        "btn_delete_profile_tip": "Permanently deletes the active profile",
        "profile_stats_template": "Saved in Profile: {apps} Apps  •  {tweaks} Tweaks  •  {backups} Backup Items",
        "settings_sys_title": "Administrator Privileges",
        "settings_sys_desc": "Required for applying Windows registry modifications and silent software installations.",
        "admin_status_active": "Administrator Rights: Active",
        "btn_restart_admin": "Restart as Administrator",
        "settings_about_title": "Keystone  •  Version 2.0 (Portable)",

        # Dialogs & Prompts
        "msg_warning": "Warning",
        "msg_info": "Information",
        "msg_success": "Operation Completed",
        "msg_error": "Error",
        "dialog_new_profile_title": "Add New Profile — Start from Scratch",
        "dialog_new_profile_header": "NEW USER PROFILE",
        "dialog_new_profile_info1": "Just like browser profiles, this profile starts completely from SCRATCH.",
        "dialog_new_profile_info2": "Your selected software, registry tweaks, and backups are stored isolated in this profile.",
        "dialog_profile_name_lbl": "Profile Name:",
        "dialog_profile_placeholder": "e.g., Gaming Rig, Workstation & Dev, Fresh 2026...",
        "dialog_btn_create_profile": "Create Profile (Start from Scratch)",
        "dialog_btn_cancel": "Cancel",
        "dialog_btn_save": "Save",
        "dialog_rename_title": "Rename Profile",
        "dialog_rename_lbl": "New Profile Name:",
        "dialog_name_empty_warning": "Please enter a valid profile name!",
        "dialog_confirm_delete_profile": "Are you sure you want to delete profile '{name}'?\nAll selections in this profile will be permanently removed.",
        "dialog_cannot_delete_last_profile": "You cannot delete the only remaining profile.",
        "dialog_select_backup_dir": "Select Target Directory for Backups",
        "dialog_select_restore_dir": "Select Directory Containing Backups",
        "dialog_no_selection_warning": "Please select at least one item to proceed!",
        "dialog_dir_not_found": "The selected directory does not exist or cannot be accessed.",
        "dialog_tweaks_applied_msg": "Selected registry tweaks have been successfully applied.",
        "dialog_tweaks_reverted_msg": "Selected tweaks have been reverted to default Windows settings."
    }
}

# Software Categories Translations
CATEGORIES_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "all": {"tr": "Tümü", "en": "All"},
    "installed": {"tr": "Kurulu", "en": "Installed"},
    "runtimes": {"tr": "Runtime", "en": "Runtimes"},
    "hardware_test": {"tr": "Donanım & Test", "en": "Hardware & Test"},
    "security": {"tr": "Güvenlik", "en": "Security"},
    "dev": {"tr": "Yazılımcı", "en": "Developer"},
    "ai": {"tr": "Yapay Zeka", "en": "AI & ML"},
    "database": {"tr": "Veritabanı", "en": "Database"},
    "virtual": {"tr": "Sanallaştırma", "en": "Virtualization"},
    "drivers": {"tr": "Sürücüler", "en": "Drivers"},
    "browsers": {"tr": "Tarayıcılar", "en": "Browsers"},
    "gaming": {"tr": "Oyun", "en": "Gaming"},
    "utilities": {"tr": "Araçlar & Medya", "en": "Utilities & Media"},
}

# Tweak Categories Translations
TWEAK_CATEGORIES_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "all": {"tr": "Tüm Ayarlar", "en": "All Tweaks"},
    "interface": {"tr": "Görünüm & Arayüz", "en": "Appearance & UI"},
    "developer": {"tr": "Yazılımcı Ayarları", "en": "Developer Tweaks"},
    "performance": {"tr": "Performans & Oyun", "en": "Performance & Gaming"},
    "system": {"tr": "Sistem & Depolama", "en": "System & Storage"},
}

# Registry Tweaks Localized Metadata
TWEAKS_EN: Dict[str, Dict[str, str]] = {
    "classic_context_menu": {
        "name": "Classic Windows 10 Context Menu",
        "short_desc": "Restores the classic, fast Windows 10 context menu instead of Windows 11 'Show more options'.",
        "full_desc": "Disables Windows 11 two-tiered context menu and restores the full instant Windows 10 style right-click menu, significantly accelerating file workflows."
    },
    "taskbar_end_task": {
        "name": "Enable Taskbar 'End Task' Option",
        "short_desc": "Adds 'End Task' directly to the right-click menu of taskbar app icons.",
        "full_desc": "Enables Windows 11 native developer 'End Task' feature, allowing you to instantly terminate frozen or unresponsive applications without opening Task Manager."
    },
    "remove_user_folders": {
        "name": "Hide User Folders from 'This PC'",
        "short_desc": "Hides 7 user folders in File Explorer and shows only disk drives.",
        "full_desc": "Cleans up File Explorer's 'This PC' view by hiding 3D Objects, Desktop, Documents, Downloads, Music, Pictures, and Videos folders, displaying storage drives immediately."
    },
    "unpin_downloads_quick_access": {
        "name": "Unpin Downloads from Quick Access / Home",
        "short_desc": "Removes pinned Downloads folder shortcut from File Explorer navigation pane.",
        "full_desc": "Safely unpins the Downloads shortcut from File Explorer Quick Access (Home) navigation tree without altering files or registry policies."
    },
    "remove_gallery": {
        "name": "Remove Gallery Icon from File Explorer",
        "short_desc": "Removes the mandatory Windows 11 'Gallery' icon from navigation pane.",
        "full_desc": "Completely removes the mandatory Windows 11 'Gallery' node from the File Explorer navigation pane for all system users."
    },
    "disable_bing_search": {
        "name": "Remove Bing Web Search from Start Menu",
        "short_desc": "Prevents Start Menu from searching the web, keeping searches purely local and fast.",
        "full_desc": "Disables Microsoft Bing web search suggestions in the Start Menu, eliminating typing latency and focusing exclusively on local file and app indexing."
    },
    "show_this_pc": {
        "name": "Show 'This PC' Icon on Desktop",
        "short_desc": "Adds the classic 'This PC' system desktop shortcut after fresh install.",
        "full_desc": "Automatically unhides and restores the classic 'This PC' (My Computer) desktop icon on fresh Windows installations."
    },
    "disable_uac_prompts": {
        "name": "Disable UAC Prompts (Never Notify)",
        "short_desc": "Suppresses administrator permission prompts to run programs directly.",
        "full_desc": "Lowers User Account Control (UAC) elevation behavior to allow administrator-level applications to execute without popup prompt interruptions."
    },
    "disable_hibernation": {
        "name": "Disable Hibernation (Reclaim 16GB+ Space)",
        "short_desc": "Removes hiberfil.sys to reclaim disk space equal to RAM size.",
        "full_desc": "Disables Windows Hibernate mode ('powercfg /h off') and deletes hiberfil.sys, freeing up 16 GB to 32 GB of SSD storage space."
    },
    "photos_legacy": {
        "name": "Microsoft Photos Legacy",
        "short_desc": "Installs the fast and classic Microsoft Photos Legacy viewer.",
        "full_desc": "Replaces the sluggish modern Photos app with the lightweight, fast-loading official Microsoft Photos Legacy application via Winget / Microsoft Store."
    },
    "developer_mode": {
        "name": "Enable Windows Developer Mode",
        "short_desc": "Allows execution of unsigned packages and developer tools.",
        "full_desc": "Activates Windows Developer Mode, enabling unrestricted execution of PowerShell scripts, sideloaded applications, and development toolchains."
    },
    "disable_telemetry": {
        "name": "Restrict Windows Diagnostic Telemetry",
        "short_desc": "Minimizes background diagnostic telemetry sent to Microsoft servers.",
        "full_desc": "Sets Windows diagnostic data collection to the minimum level, reducing background CPU and disk activity while enhancing privacy."
    },
    "fast_reboot": {
        "name": "Shorten Shutdown and Reboot Timeout",
        "short_desc": "Reduces hung application shutdown timeout (HungAppTimeout).",
        "full_desc": "Reduces wait time for hanging applications during system shutdown or restart from 5 seconds to 1-2 seconds, accelerating power-down."
    },
    "clear_icon_cache": {
        "name": "Rebuild Windows Icon Cache",
        "short_desc": "Resets IconCache.db to fix broken, missing, or white blank taskbar icons.",
        "full_desc": "Purges Windows IconCache.db and Explorer thumbnail databases and restarts File Explorer to restore corrupted or blank application icons."
    }
}

# Backup Items Localized Metadata
BACKUP_EN: Dict[str, Dict[str, str]] = {
    "browsers": {
        "name": "Browser Bookmarks (HTML & Profile)",
        "short_desc": "Exports universal HTML bookmarks and profile data for Brave, Chrome, Edge, Firefox, etc.",
        "full_desc": "Exports bookmarks from all installed browsers into universal Netscape 'bookmarks.html' format, enabling seamless one-click import or automatic profile restoration."
    },
    "wifi": {
        "name": "Saved Wi-Fi Networks & Passwords",
        "short_desc": "Exports all saved Wi-Fi networks and security keys to XML.",
        "full_desc": "Backs up all saved wireless connection profiles with decrypted security keys, allowing instant one-click restoration on fresh installations."
    },
    "vscode": {
        "name": "VS Code Settings & Extensions",
        "short_desc": "Backs up settings.json, keybindings, snippets, and installed extension list.",
        "full_desc": "Exports Visual Studio Code editor configuration, custom keybindings, snippets, and extension list, reinstalling extensions automatically post-format."
    },
    "dev_environment": {
        "name": "Developer & Terminal Profiles (Git, SSH, Terminal, PATH)",
        "short_desc": "Backs up Git config, SSH keys, Windows Terminal profiles, and User PATH.",
        "full_desc": "Consolidates developer essentials including ~/.gitconfig, ~/.ssh keys, Windows Terminal settings.json, PowerShell $PROFILE, and User Environment PATH variables."
    },
    "installed_apps": {
        "name": "Installed Applications & Winget Manifest",
        "short_desc": "Scans all installed software and exports Winget package manifests.",
        "full_desc": "Inspects system registry uninstall hives and Winget packages to generate kurulu_programlar.txt, installed_programs.json, and winget_packages.json manifests."
    },
    "active_tweaks": {
        "name": "Active Windows Registry (Regedit) Tweaks",
        "short_desc": "Exports active Windows registry optimizations into .reg and JSON manifests.",
        "full_desc": "Backs up all currently active Keystone and system tweaks into a valid .reg Registry file and JSON manifest for one-click re-application on fresh Windows."
    }
}

# Software Packages Localized Metadata (English)
PACKAGES_EN: Dict[str, Dict[str, str]] = {
    "directx": {
        "name": "DirectX End-User Runtimes",
        "short_desc": "Essential DirectX 9, 10, and 11 runtime libraries for modern and legacy games.",
        "full_desc": "Required for post-format gaming to prevent 'd3dx9_xx.dll not found' errors. Installs full legacy and modern DirectX components."
    },
    "vcredist_aio": {
        "name": "Visual C++ All-in-One (2005-2022)",
        "short_desc": "All Visual C++ redistributable packages (2005 to 2022, x86/x64).",
        "full_desc": "Prevents missing 'MSVCP140.dll' and 'VCRUNTIME140.dll' runtime errors. Installs all Visual C++ libraries from 2005 through 2022 in a single silent setup."
    },
    "dotnet_desktop_10": {
        "name": "Microsoft .NET 10.0 Desktop Runtime",
        "short_desc": "Runtime environment for latest generation .NET 10 Windows desktop apps.",
        "full_desc": "Official Microsoft runtime for modern Windows desktop (WPF and WinForms) applications built with .NET 10 architecture."
    },
    "klite_codec": {
        "name": "K-Lite Codec Pack Full",
        "short_desc": "Comprehensive codec pack to play all video and audio formats (MKV, FLAC, HEVC, AV1).",
        "full_desc": "Installs complete collection of multimedia codecs for Windows. Bundled with high-quality MPC-HC player, madVR renderer, and LAV Filters."
    },
    "jdk": {
        "name": "Java Development Kit (JDK 21/23)",
        "short_desc": "Java runtime and developer environment for Minecraft, NetBeans, and Eclipse.",
        "full_desc": "Installs official Java Development Kit (OpenJDK/Oracle JDK) environment required for Java applications, Minecraft, and backend software development."
    },
    "ffmpeg": {
        "name": "FFmpeg",
        "short_desc": "Multimedia processing, transcoding, and video/audio conversion library.",
        "full_desc": "Universal command-line tool and multimedia libraries for recording, converting, and streaming digital audio and video formats."
    },
    "git": {
        "name": "Git for Windows",
        "short_desc": "Distributed version control system with Git Bash and Windows Shell integration.",
        "full_desc": "Industry-standard version control system for tracking source code changes. Includes Git Bash, Git GUI, and Shell context menu tools."
    },
    "python": {
        "name": "Python 3 (Latest)",
        "short_desc": "Official Python programming language runtime with pip and PATH registration.",
        "full_desc": "Official Python interpreter with automatic PATH registration, pip package manager, and IDLE development environment."
    },
    "vscode": {
        "name": "Visual Studio Code",
        "short_desc": "Lightweight and extensible code editor for modern web and cloud applications.",
        "full_desc": "Microsoft's flagship source-code editor with built-in debugging support, Git commands, syntax highlighting, and rich extension ecosystem."
    },
    "vs_community": {
        "name": "Visual Studio 2022 Community",
        "short_desc": "Comprehensive IDE for .NET, C++, Windows desktop, and game development.",
        "full_desc": "Full-featured integrated development environment for building modern Windows desktop applications, C++ games, and enterprise .NET solutions."
    },
    "pycharm": {
        "name": "PyCharm Community",
        "short_desc": "Python IDE with intelligent code completion and integrated debugging.",
        "full_desc": "Dedicated Python development environment featuring smart code navigation, inspection, test runner, and debugger."
    },
    "anaconda": {
        "name": "Anaconda Distribution",
        "short_desc": "Python data science and machine learning platform with conda package manager.",
        "full_desc": "Comprehensive Python data science distribution bundled with Jupyter, NumPy, Pandas, SciPy, and conda environment management."
    },
    "nodejs": {
        "name": "Node.js (LTS)",
        "short_desc": "JavaScript runtime environment with npm package manager.",
        "full_desc": "Cross-platform JavaScript runtime environment for backend development, tooling, and front-end build pipelines."
    },
    "powertoys": {
        "name": "Microsoft PowerToys",
        "short_desc": "Productivity utilities to tune and streamline Windows workflows.",
        "full_desc": "Set of Windows system utilities for power users, including FancyZones, PowerToys Run launcher, Text Extractor, and Color Picker."
    },
    "windows_terminal": {
        "name": "Windows Terminal",
        "short_desc": "Modern, fast, and powerful multi-tab terminal for PowerShell and WSL.",
        "full_desc": "Official Microsoft multi-tab terminal with GPU acceleration, custom themes, split panes, and support for PowerShell, CMD, and WSL."
    },
    "github_desktop": {
        "name": "GitHub Desktop",
        "short_desc": "Seamless Git and GitHub graphical workflow client.",
        "full_desc": "Simple, visual collaboration client for Git repositories with branch visualization and PR review workflows."
    },
    "sublime_text": {
        "name": "Sublime Text 4",
        "short_desc": "Sophisticated text editor for code, markup, and prose with lightning performance.",
        "full_desc": "Blazing fast text editor with GPU rendering, supercharged tab management, and extensive package ecosystem."
    },
    "postman": {
        "name": "Postman",
        "short_desc": "API development, testing, and collaboration platform.",
        "full_desc": "Complete API platform for building, designing, testing, and automating REST, GraphQL, and WebSocket APIs."
    },
    "firefox": {
        "name": "Mozilla Firefox",
        "short_desc": "Fast, private, and open-source web browser with tracking protection.",
        "full_desc": "Privacy-focused web browser featuring enhanced tracking protection, multi-account containers, and comprehensive extension support."
    },
    "7zip": {
        "name": "7-Zip",
        "short_desc": "High-compression file archiver supporting 7z, ZIP, RAR, TAR, and GZ formats.",
        "full_desc": "High-efficiency open-source file archiver with industry-leading compression ratios and Windows Explorer shell integration."
    },
    "winrar": {
        "name": "WinRAR",
        "short_desc": "Industry standard RAR and ZIP file compression and archive manager.",
        "full_desc": "Powerful archive manager that can create, manage, and unpack RAR, ZIP, and other compressed archive files."
    },
    "discord": {
        "name": "Discord",
        "short_desc": "Voice, video, and text communication platform for communities and gamers.",
        "full_desc": "Popular voice and text chat platform featuring low-latency voice channels, screen sharing, and direct messaging."
    },
    "obsidian": {
        "name": "Obsidian",
        "short_desc": "Extensible Markdown-based knowledge base and note-taking application.",
        "full_desc": "Privacy-first, local Markdown note-taking tool with graph view, bidirectional linking, and vast plugin library."
    },
    "docker": {
        "name": "Docker Desktop",
        "short_desc": "Containerization platform to build, share, and run containerized applications.",
        "full_desc": "Complete developer toolset for container creation, deployment, and management using Docker and Kubernetes on Windows."
    },
    "dbeaver": {
        "name": "DBeaver Community",
        "short_desc": "Universal multi-database management tool and SQL client.",
        "full_desc": "Universal graphical database management tool supporting PostgreSQL, MySQL, SQLite, Oracle, SQL Server, and more."
    }
}


def get_language() -> str:
    """Returns the currently active language code ('tr' or 'en')."""
    return _CURRENT_LANG


def set_language(lang: str) -> None:
    """Sets the active language code."""
    global _CURRENT_LANG
    if lang in ("tr", "en"):
        _CURRENT_LANG = lang


def t(key: str, **kwargs) -> str:
    """Translates a key into the active language with optional formatting kwargs."""
    lang_dict = STRINGS.get(_CURRENT_LANG, STRINGS["tr"])
    text = lang_dict.get(key, STRINGS["tr"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def get_category_name(cat_id: str, is_tweak: bool = False, lang: Optional[str] = None) -> str:
    """Returns localized category name."""
    l = lang or _CURRENT_LANG
    if is_tweak:
        mapping = TWEAK_CATEGORIES_TRANSLATIONS.get(cat_id, {})
    else:
        mapping = CATEGORIES_TRANSLATIONS.get(cat_id, {})
    return mapping.get(l, mapping.get("tr", cat_id))


def get_package_meta(pkg: dict, lang: Optional[str] = None) -> Tuple[str, str, str]:
    """Returns (name, short_desc, full_desc) for a package in the specified or active language."""
    l = lang or _CURRENT_LANG
    p_id = pkg.get("id", "")
    if l == "en" and p_id in PACKAGES_EN:
        en = PACKAGES_EN[p_id]
        return en.get("name", pkg.get("name", "")), en.get("short_desc", pkg.get("short_desc", "")), en.get("full_desc", pkg.get("full_desc", ""))
    return pkg.get("name", ""), pkg.get("short_desc", ""), pkg.get("full_desc", "")


def get_tweak_meta(tweak: dict, lang: Optional[str] = None) -> Tuple[str, str, str]:
    """Returns (name, short_desc, full_desc) for a tweak in the specified or active language."""
    l = lang or _CURRENT_LANG
    t_id = tweak.get("id", "")
    if l == "en" and t_id in TWEAKS_EN:
        en = TWEAKS_EN[t_id]
        return en["name"], en["short_desc"], en["full_desc"]
    return tweak.get("name", ""), tweak.get("short_desc", ""), tweak.get("full_desc", "")


def get_backup_meta(item: dict, lang: Optional[str] = None) -> Tuple[str, str, str]:
    """Returns (name, short_desc, full_desc) for a backup item in the specified or active language."""
    l = lang or _CURRENT_LANG
    b_id = item.get("id", "")
    if l == "en" and b_id in BACKUP_EN:
        en = BACKUP_EN[b_id]
        return en["name"], en["short_desc"], en["full_desc"]
    return item.get("name", ""), item.get("short_desc", ""), item.get("full_desc", "")
