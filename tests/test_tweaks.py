import pytest

from keystone.core.proc import Result
from keystone.tweaks import all_tweaks
from keystone.tweaks.engine import Backends, Cmd, Defaults, GSettings, Reg, RegKey


class FakeRegistry:
    def __init__(self):
        self.vals = {}     # (hive, key.lower(), name) -> value
        self.keys = set()

    def _k(self, hive, key):
        return hive, key.lower()

    def get(self, hive, key, name):
        k = (*self._k(hive, key), name)
        return (k in self.vals), self.vals.get(k)

    def set(self, hive, key, name, kind, value):
        assert kind in ("DWORD", "SZ", "EXPAND_SZ", "QWORD")
        self.keys.add(self._k(hive, key))
        self.vals[(*self._k(hive, key), name)] = value

    def delete_value(self, hive, key, name):
        self.vals.pop((*self._k(hive, key), name), None)

    def key_exists(self, hive, key):
        return self._k(hive, key) in self.keys

    def delete_key(self, hive, key):
        h, k = self._k(hive, key)
        self.keys = {x for x in self.keys if not (x[0] == h and (x[1] == k or x[1].startswith(k + "\\")))}
        self.vals = {x: v for x, v in self.vals.items() if not (x[0] == h and (x[1] == k or x[1].startswith(k + "\\")))}


class FakeShell:
    """Emulates `defaults` and `gsettings` well enough for round-trips."""

    def __init__(self):
        self.store = {}
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        tool, verb, *rest = cmd
        if tool == "defaults":
            if verb == "write":
                dom, key, kind, val = rest
                if kind == "-bool":
                    val = "1" if val == "true" else "0"
                self.store[(dom, key)] = val
                return Result(0, "")
            if verb == "read":
                k = tuple(rest)
                return Result(0, self.store[k] + "\n") if k in self.store else Result(1, "does not exist")
            if verb == "delete":
                self.store.pop(tuple(rest), None)
                return Result(0, "")
        if tool == "gsettings":
            if verb == "set":
                self.store[(rest[0], rest[1])] = rest[2]
                return Result(0, "")
            if verb == "get":
                return Result(0, self.store.get((rest[0], rest[1]), "'default'") + "\n")
            if verb == "reset":
                self.store.pop((rest[0], rest[1]), None)
                return Result(0, "")
        return Result(0, "")


def test_ids_unique_and_bilingual():
    ids = []
    for os_, ts in all_tweaks().items():
        for t in ts:
            assert t.os == os_
            assert t.name["tr"] and t.name["en"] and t.desc["tr"] and t.desc["en"], t.id
            ids.append(t.id)
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("t", [t for t in all_tweaks()["windows"]
                               if all(isinstance(o, (Reg, RegKey)) for o in t.ops)], ids=lambda t: t.id)
def test_windows_registry_tweaks_roundtrip(t):
    b = Backends(registry=FakeRegistry(), run=lambda *a, **k: Result(0, ""))
    assert t.state(b) is False
    t.apply(b)
    assert t.state(b) is True
    t.revert(b)
    assert t.state(b) is False


def test_appx_removal_roundtrip():
    from keystone.tweaks import windows

    installed = {"Clipchamp.Clipchamp"}
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        text = " ".join(cmd)
        if "Remove-AppxPackage" in text:
            installed.clear()
        elif cmd[0] == "winget":
            installed.add("Clipchamp.Clipchamp")
        return Result(0, "\n".join(installed))

    windows._appx_forget()
    t = next(x for x in all_tweaks()["windows"] if x.id == "remove_clipchamp")
    b = Backends(registry=FakeRegistry(), run=run)
    assert t.state(b) is False
    t.apply(b)
    assert t.state(b) is True
    t.revert(b)
    assert t.state(b) is False
    assert calls[-2][:3] == ["winget", "install", "--id"]
    windows._appx_forget()


def test_appx_failure_is_reported():
    from keystone.tweaks.windows import Appx
    with pytest.raises(RuntimeError):
        Appx(["Microsoft.Copilot"]).apply(Backends(run=lambda *a, **k: Result(1, "denied")))


def test_store_apps_without_id_are_one_shot():
    ts = {t.id: t for t in all_tweaks()["windows"]}
    assert ts["remove_solitaire"].action and not ts["remove_teams"].action


def test_onedrive_removal_asks_first_and_blocks_return():
    t = next(x for x in all_tweaks()["windows"] if x.id == "remove_onedrive")
    assert t.risk == "high" and t.admin
    reg = FakeRegistry()
    seen = []
    t.apply(Backends(registry=reg, run=lambda cmd, **k: seen.append(cmd) or Result(0, "")))
    assert reg.get("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\OneDrive", "DisableFileSyncNGSC") == (True, 1)
    t.revert(Backends(registry=reg, run=lambda cmd, **k: seen.append(cmd) or Result(0, "")))
    assert seen[-1][:2] == ["winget", "install"]
    assert not reg.vals


def test_classic_menu_revert_removes_whole_clsid():
    t = next(x for x in all_tweaks()["windows"] if x.id == "classic_context_menu")
    reg = FakeRegistry()
    b = Backends(registry=reg)
    t.apply(b)
    assert any("inprocserver32" in k for _, k in reg.keys)
    t.revert(b)
    assert not reg.keys


def test_menu_show_delay_tweak():
    t = next(x for x in all_tweaks()["windows"] if x.id == "menu_show_delay")
    reg = FakeRegistry()
    b = Backends(registry=reg)
    t.apply(b)
    exists, val = reg.get("HKCU", r"Control Panel\Desktop", "MenuShowDelay")
    assert exists and val == "0"
    t.revert(b)
    exists, val = reg.get("HKCU", r"Control Panel\Desktop", "MenuShowDelay")
    assert exists and val == "400"


def test_user_folders_tweak_writes_both_views():
    t = next(x for x in all_tweaks()["windows"] if x.id == "remove_user_folders")
    reg = FakeRegistry()
    t.apply(Backends(registry=reg))
    assert len(reg.vals) == 14 and set(reg.vals.values()) == {"Hide"}
    t.revert(Backends(registry=reg))
    assert set(reg.vals.values()) == {"Show"}


@pytest.mark.parametrize("t", [t for t in all_tweaks()["macos"] if all(isinstance(o, Defaults) for o in t.ops)],
                         ids=lambda t: t.id)
def test_macos_defaults_roundtrip(t):
    b = Backends(run=FakeShell())
    assert t.state(b) is False
    t.apply(b)
    assert t.state(b) is True
    t.revert(b)
    assert t.state(b) is False


@pytest.mark.parametrize("t", [t for t in all_tweaks()["linux"] if all(isinstance(o, GSettings) for o in t.ops)],
                         ids=lambda t: t.id)
def test_gnome_roundtrip(t):
    b = Backends(run=FakeShell())
    assert t.state(b) is False
    t.apply(b)
    assert t.state(b) is True
    t.revert(b)
    assert t.state(b) is False


def test_root_commands_are_elevated(monkeypatch):
    from keystone.core import proc, system
    monkeypatch.setattr(proc, "detect", lambda: system.SystemInfo("linux", "x", "1", "x64", is_admin=False))
    monkeypatch.setattr(proc, "which", lambda n: "/usr/bin/pkexec" if n == "pkexec" else None)
    monkeypatch.setenv("DISPLAY", ":0")
    seen = []
    Cmd(["systemctl", "enable", "--now", "fstrim.timer"], root=True).apply(
        Backends(run=lambda cmd, **kw: seen.append(cmd) or Result(0, "")))
    assert seen[0][:2] == ["pkexec", "systemctl"]


def test_failed_command_raises():
    with pytest.raises(RuntimeError):
        GSettings("a", "b", "true").apply(Backends(run=lambda *a, **k: Result(1, "No such schema")))


def test_risky_tweaks_carry_a_bilingual_warning():
    for ts in all_tweaks().values():
        for t in ts:
            if t.risk in ("medium", "high"):
                assert t.warn.get("tr") and t.warn.get("en"), t.id
            assert t.meta()["warn"] == t.warn


def test_lock_screen_timeout_extend_roundtrip():
    ts = {t.id: t for t in all_tweaks()["windows"]}
    t = ts["lock_screen_timeout_extend"]
    calls = []
    b = Backends(registry=FakeRegistry(), run=lambda cmd, **kw: calls.append(cmd) or Result(0, ""))
    assert t.state(b) is False
    t.apply(b)
    assert t.state(b) is True
    assert any("1800" in " ".join(c) for c in calls)
    t.revert(b)
    assert t.state(b) is False
    assert any("60" in " ".join(c) for c in calls)


def test_lock_screen_timeout_unhide():
    ts = {t.id: t for t in all_tweaks()["windows"]}
    assert ts["lock_screen_timeout_unhide"].admin is True


def test_windows_features_exist():
    ts = {t.id: t for t in all_tweaks()["windows"]}
    for fid in ("wsl2", "virtual_machine_platform", "hyper_v", "windows_sandbox",
                "windows_hypervisor_platform", "telnet_client", "netfx3"):
        assert fid in ts
        t = ts[fid]
        assert t.admin is True
        assert t.name["tr"] and t.name["en"]
        assert t.desc["tr"] and t.desc["en"]


def test_dism_feature_roundtrip():
    from keystone.tweaks.windows import _clear_feature_cache

    ts = {t.id: t for t in all_tweaks()["windows"]}
    t = ts["wsl2"]
    calls = []
    features_state = {"Microsoft-Windows-Subsystem-Linux": 2, "VirtualMachinePlatform": 2}

    def fake_run(cmd, **kw):
        calls.append(cmd)
        cmd_str = " ".join(cmd)
        if "Get-CimInstance" in cmd_str:
            lines = ['"Name","InstallState"']
            for name, st in features_state.items():
                lines.append(f'"{name}","{st}"')
            return Result(0, "\n".join(lines))
        if "/Enable-Feature" in cmd_str:
            for feat in features_state:
                if f"/FeatureName:{feat}" in cmd_str:
                    features_state[feat] = 1
            return Result(0, "")
        if "/Disable-Feature" in cmd_str:
            for feat in features_state:
                if f"/FeatureName:{feat}" in cmd_str:
                    features_state[feat] = 2
            return Result(0, "")
        return Result(0, "")

    _clear_feature_cache()
    b = Backends(registry=FakeRegistry(), run=fake_run)
    assert t.state(b) is False
    t.apply(b)
    assert t.state(b) is True
    assert any("/Enable-Feature" in " ".join(c) for c in calls)
    t.revert(b)
    assert t.state(b) is False
    assert any("/Disable-Feature" in " ".join(c) for c in calls)
    _clear_feature_cache()


def test_reboot_to_bios_script_tweak(tmp_path, monkeypatch):
    from keystone.tweaks import windows

    ts = {t.id: t for t in all_tweaks()["windows"]}
    assert "reboot_to_bios_script" in ts
    t = ts["reboot_to_bios_script"]
    assert t.category == "system"
    assert t.action is True
    assert t.name["tr"] and t.name["en"]
    assert t.desc["tr"] and t.desc["en"]

    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    b = Backends(registry=FakeRegistry(), run=lambda *a, **k: Result(0, ""))

    assert t.state(b) is None
    assert t.ops[0].check(b) is False
    t.apply(b)
    assert t.ops[0].check(b) is True
    target = tmp_path / "Desktop" / "BIOS_Yeniden_Baslat.bat"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "shutdown.exe /r /fw /t 2" in content
    assert "powershell" in content
    assert "RunAs" in content
    t.revert(b)
    assert t.ops[0].check(b) is False
    assert not target.exists()


def test_run_mrt_tweak():
    from keystone.tweaks import windows

    ts = {t.id: t for t in all_tweaks()["windows"]}
    assert "run_mrt" in ts
    t = ts["run_mrt"]
    assert t.category == "maintenance"
    assert t.action is True
    assert t.admin is True
    assert t.name["tr"] and t.name["en"]
    assert t.desc["tr"] and t.desc["en"]
    assert "MRT" in t.name["tr"]

    calls = []
    b = Backends(registry=FakeRegistry(), run=lambda cmd, **kw: (calls.append(cmd), Result(0, ""))[1])
    assert t.state(b) is None
    t.apply(b)
    assert len(calls) == 1
    assert any("MRT.exe" in part for part in calls[0])
