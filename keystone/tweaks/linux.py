"""Linux tweaks: GNOME (gsettings) for desktop behaviour, drop-in files and
systemd units for system behaviour."""
from __future__ import annotations

from ..core import proc
from .engine import Cmd, GSettings, RootFile, Tweak

L = "linux"
IFACE = "org.gnome.desktop.interface"


def _t(id, cat, tr, en, dtr, den, ops, **kw) -> Tweak:
    return Tweak(id, L, cat, {"tr": tr, "en": en}, {"tr": dtr, "en": den}, ops, **kw)


def _unit_enabled(unit: str):
    return lambda b: b.run(["systemctl", "is-enabled", unit], timeout=15).out.strip() == "enabled"


def _flathub_present(b) -> bool:
    return "flathub" in b.run(["flatpak", "remotes", "--columns=name"], timeout=30).out.split()


TWEAKS: list[Tweak] = [
    _t("gnome_dark", "interface", "Koyu tema", "Dark style",
       "GNOME ve GTK uygulamaları için koyu stili açar.", "Prefer the dark style in GNOME and GTK apps.",
       [GSettings(IFACE, "color-scheme", "'prefer-dark'")], requires="gnome", recommended=True),
    _t("gnome_window_buttons", "interface", "Küçült ve büyüt düğmeleri", "Minimise & maximise buttons",
       "Pencere başlığına GNOME'un gizlediği küçült ve büyüt düğmelerini ekler.",
       "Bring back the minimise and maximise buttons GNOME hides.",
       [GSettings("org.gnome.desktop.wm.preferences", "button-layout", "'appmenu:minimize,maximize,close'")],
       requires="gnome", recommended=True),
    _t("gnome_battery_percent", "interface", "Pil yüzdesi", "Battery percentage",
       "Üst çubukta pil yüzdesini gösterir.", "Show the battery percentage in the top bar.",
       [GSettings(IFACE, "show-battery-percentage", "true")], requires="gnome", recommended=True),
    _t("gnome_clock_weekday", "interface", "Saatte gün adı", "Weekday in clock",
       "Üst çubuktaki saate haftanın gününü ekler.", "Add the weekday to the top-bar clock.",
       [GSettings(IFACE, "clock-show-weekday", "true")], requires="gnome"),
    _t("gnome_no_hot_corner", "interface", "Sıcak köşeyi kapat", "Disable hot corner",
       "Fare sol üst köşeye gidince Etkinlikler'in açılmasını engeller.",
       "Stop Activities from opening when the pointer hits the top-left corner.",
       [GSettings(IFACE, "enable-hot-corners", "false")], requires="gnome"),
    _t("gnome_center_windows", "interface", "Yeni pencereleri ortala", "Centre new windows",
       "Yeni açılan pencereler ekranın ortasında başlar.", "Open new windows in the centre of the screen.",
       [GSettings("org.gnome.mutter", "center-new-windows", "true")], requires="gnome"),
    _t("gnome_tap_to_click", "interface", "Dokunarak tıkla", "Tap to click",
       "Touchpad'e hafifçe dokunmak tıklama sayılır.", "A light tap on the touchpad counts as a click.",
       [GSettings("org.gnome.desktop.peripherals.touchpad", "tap-to-click", "true")], requires="gnome", recommended=True),
    _t("gnome_night_light", "interface", "Gece ışığı", "Night light",
       "Akşamları ekran rengini otomatik olarak sıcaklaştırır.", "Warm the screen colour automatically in the evening.",
       [GSettings("org.gnome.settings-daemon.plugins.color", "night-light-enabled", "true")], requires="gnome"),
    _t("gnome_no_animations", "performance", "Animasyonları kapat", "Disable animations",
       "Arayüz animasyonlarını kapatarak eski donanımda daha çevik his verir.",
       "Turn off interface animations for a snappier feel on older hardware.",
       [GSettings(IFACE, "enable-animations", "false")], requires="gnome"),
    _t("swappiness", "performance", "Takas kullanımını azalt", "Lower swappiness",
       "Bellek doluyken diske takas yapmayı geciktirir (vm.swappiness=10). Masaüstünde daha akıcı.",
       "Delay swapping to disk (vm.swappiness=10) for a smoother desktop.",
       [RootFile("/etc/sysctl.d/99-keystone-swappiness.conf", "vm.swappiness=10\n",
                 after=["sysctl", "--system"])], admin=True, recommended=True),
    _t("fstrim_timer", "performance", "Haftalık SSD TRIM", "Weekly SSD TRIM",
       "SSD performansını korumak için haftalık fstrim zamanlayıcısını açar.",
       "Enable the weekly fstrim timer to keep SSDs fast.",
       [Cmd(["systemctl", "enable", "--now", "fstrim.timer"], ["systemctl", "disable", "--now", "fstrim.timer"],
            probe=_unit_enabled("fstrim.timer"), root=True)], admin=True, recommended=True, requires="systemctl"),
    _t("flathub", "system", "Flathub deposunu ekle", "Add Flathub",
       "Binlerce masaüstü uygulamasının bulunduğu Flathub'ı kullanıcı deposu olarak ekler.",
       "Add Flathub, home of thousands of desktop apps, as a per-user remote.",
       [Cmd(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
             "https://dl.flathub.org/repo/flathub.flatpakrepo"],
            ["flatpak", "remote-delete", "--user", "flathub"], probe=_flathub_present)],
       requires="flatpak", recommended=True),
    _t("firewall_ufw", "privacy", "Güvenlik duvarını aç (ufw)", "Enable firewall (ufw)",
       "Gelen bağlantıları varsayılan olarak engelleyen ufw güvenlik duvarını açar.",
       "Turn on the ufw firewall with incoming connections denied by default.",
       [Cmd(["ufw", "--force", "enable"], ["ufw", "disable"],
            probe=None, root=True)], admin=True, requires="ufw"),
    _t("clean_journal", "maintenance", "Günlükleri küçült", "Shrink system logs",
       "systemd günlüklerini son 2 haftayla sınırlar ve yer açar.",
       "Trim systemd journals to the last two weeks to free space.",
       [Cmd(["journalctl", "--vacuum-time=2weeks"], root=True)], action=True, admin=True, requires="journalctl"),
]


def restart_shell(which: str) -> None:  # GNOME applies gsettings live
    return None


def requirement_met(req: str, desktop: str) -> bool:
    if not req:
        return True
    if req == "gnome":
        return desktop in ("gnome", "ubuntu", "pop", "budgie", "unity") and proc.run(["gsettings", "--version"], timeout=5).ok
    from ..core.system import which
    return which(req) is not None
