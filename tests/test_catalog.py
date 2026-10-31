from keystone import catalog
from keystone.pkg.registry import ALL, candidate_names, resolve


def mgrs(*names):
    return {n: ALL[n]() for n in names}

from .conftest import host  # noqa: E402


def test_catalog_integrity():
    pkgs = catalog.load()
    ids = [p["id"] for p in pkgs]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for p in pkgs:
        assert p["category"] in catalog.CATEGORIES, p["id"]
        assert p["desc"]["tr"] and p["desc"]["en"], p["id"]
        assert catalog.platforms(p), f"{p['id']} has no platform"
        for target in p.get("alt", {}).values():
            assert target in ids
        for s in p.get("mac", []):
            assert set(s) <= {"cask", "brew"}
        for k in p.get("linux", {}):
            assert k in ("apt", "dnf", "pacman", "zypper", "flatpak", "snap")


def test_platform_coverage():
    pkgs = catalog.load()
    n = {o: sum(1 for p in pkgs if o in catalog.platforms(p)) for o in ("windows", "macos", "linux")}
    assert n["windows"] >= 150 and n["macos"] >= 80 and n["linux"] >= 60


def test_candidate_managers_per_distro():
    assert candidate_names(host("linux", "ubuntu")) == ["apt", "flatpak", "snap"]
    assert candidate_names(host("linux", "linuxmint", ["ubuntu", "debian"])) == ["apt", "flatpak", "snap"]
    assert candidate_names(host("linux", "fedora")) == ["dnf", "flatpak", "snap"]
    assert candidate_names(host("linux", "endeavouros", ["arch"])) == ["pacman", "flatpak", "snap"]
    assert candidate_names(host("linux", "opensuse-tumbleweed", ["opensuse", "suse"]))[0] == "zypper"
    assert candidate_names(host("macos")) == ["brew"]
    assert candidate_names(host("windows")) == ["winget"]


def test_resolve_prefers_native_then_flatpak():
    vlc = catalog.by_id()["vlc"]
    u = host("linux", "ubuntu")
    assert [s.pm for s in resolve(vlc, u, mgrs("apt", "flatpak"))] == ["apt", "flatpak"]
    assert [s.pm for s in resolve(vlc, u, mgrs("apt", "flatpak"), prefer="flatpak")] == ["flatpak", "apt"]
    # Chrome has only a flatpak id: unavailable until flatpak exists.
    chrome = catalog.by_id()["chrome"]
    assert resolve(chrome, u, mgrs("apt")) == []
    assert resolve(chrome, u, mgrs("apt", "flatpak"))[0].id == "com.google.Chrome"


def test_resolve_macos_and_windows():
    m = resolve(catalog.by_id()["vscode"], host("macos"), mgrs("brew"))[0]
    assert (m.pm, m.id, m.kind) == ("brew", "visual-studio-code", "cask")
    g = resolve(catalog.by_id()["git"], host("macos"), mgrs("brew"))[0]
    assert g.kind == "formula"
    w = resolve(catalog.by_id()["vcredist_aio"], host("windows"), mgrs("winget"))
    assert [s.id for s in w] == ["abbodi1406.vcredist", "Microsoft.VCRedist.2015+.x64", "Microsoft.VCRedist.2015+.x86"]
    assert resolve(catalog.by_id()["vcredist_aio"], host("macos"), mgrs("brew")) == []


def test_windows_backup_restored_on_mac_uses_alternatives():
    plan = catalog.map_for_restore(["vscode", "potplayer", "vcredist_aio", "winrar", "nope"], host("macos"), mgrs("brew"))
    by = {p["from"]: p for p in plan}
    assert by["vscode"]["action"] == "install"
    assert by["potplayer"] == {"from": "potplayer", "to": "iina", "action": "alternative"}
    assert by["winrar"]["to"] == "keka"
    assert by["vcredist_aio"]["action"] == "skip"
    assert by["nope"]["reason"] == "unknown"


def test_view_marks_installed():
    info = host("linux", "ubuntu")
    v = {p["id"]: p for p in catalog.view(info, mgrs("apt"), {"apt": {"git"}})}
    assert v["git"]["status"] == "installed"
    assert v["vlc"]["status"] == "available"
    assert v["chrome"]["status"] == "needs_manager" and v["chrome"]["missing_managers"] == ["flatpak"]
    assert v["directx"]["status"] == "unsupported"


def test_apt_batches_update_and_install_in_one_command():
    from keystone.pkg.base import Source
    cmd = ALL["apt"]().install_cmd([Source("apt", "git"), Source("apt", "vlc")])
    assert cmd[:2] == ["sh", "-c"] and "apt-get update" in cmd[2] and "install -y -q git vlc" in cmd[2]
    pac = ALL["pacman"]().install_cmd([Source("pacman", "git")])
    assert pac[:2] == ["pacman", "-Syu"]
