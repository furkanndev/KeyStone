import json

import pytest

from keystone import startup
from keystone.api import PUBLIC, Api
from keystone.core.proc import Result
from keystone.startup import (APPROVED, ENABLED_FLAG, NeedsAdmin, StartupManager, disabled_flag, is_disabled,
                              program_of)
from keystone.store import Store
from tests.conftest import host


class FakeStartupRegistry:
    def __init__(self):
        self.vals = {}      # (hive, key.lower()) -> {name: str}
        self.bins = {}      # (hive, key.lower(), name) -> bytes
        self.names = {}     # (hive, key.lower()) -> key as written, so subkey names keep their case
        self.readonly = set()

    def values(self, hive, key):
        return [(n, v) for n, v in self.vals.get((hive, key.lower()), {}).items() if isinstance(v, str)]

    def subkeys(self, hive, key):
        prefix = key.lower() + "\\"
        out = []
        for (h, k) in list(self.vals):
            if h == hive and k.startswith(prefix):
                original = self.names.get((h, k), k)
                first = original[len(prefix):].split("\\")[0]
                if first and first not in out:
                    out.append(first)
        return out

    def get_value(self, hive, key, name):
        return self.vals.get((hive, key.lower()), {}).get(name)

    def put(self, hive, key, **values):
        self.names[(hive, key.lower())] = key
        self.vals.setdefault((hive, key.lower()), {}).update(values)

    def set_string(self, hive, key, name, value):
        self.vals.setdefault((hive, key.lower()), {})[name] = value

    def get_binary(self, hive, key, name):
        return self.bins.get((hive, key.lower(), name))

    def _check(self, hive):
        if hive in self.readonly:
            raise NeedsAdmin("denied")

    def set_binary(self, hive, key, name, data):
        self._check(hive)
        self.bins[(hive, key.lower(), name)] = data

    def delete_value(self, hive, key, name):
        self._check(hive)
        self.vals.get((hive, key.lower()), {}).pop(name, None)
        self.bins.pop((hive, key.lower(), name), None)


def mgr(tmp_path, reg=None, tasks=None, run=None):
    reg = reg or FakeStartupRegistry()
    user_dir = tmp_path / "Startup"
    user_dir.mkdir(exist_ok=True)

    def fake_run(cmd, **kw):
        if run:
            return run(cmd, **kw)
        return Result(0, json.dumps(tasks if tasks is not None else []))

    m = StartupManager(host("windows"), reg=reg, run=fake_run, folders=[(str(user_dir), "user", "HKCU")])
    return m, reg, user_dir


def test_flag_encoding_matches_task_manager():
    assert ENABLED_FLAG == bytes.fromhex("020000000000000000000000")
    d = disabled_flag(now=0)
    assert d[:4] == b"\x03\x00\x00\x00" and len(d) == 12
    assert int.from_bytes(d[4:], "little") == 11644473600 * 10_000_000
    assert is_disabled(d) and not is_disabled(ENABLED_FLAG) and not is_disabled(None)
    assert not is_disabled(b"\x06\x00")      # 06 is "enabled" too (even first byte)


def test_program_of_handles_quotes_and_args():
    assert program_of('"C:\\Program Files\\A\\a.exe" --tray') == "C:\\Program Files\\A\\a.exe"
    assert program_of("C:\\Program Files (x86)\\IDM\\IDMan.exe /onboot") == "C:\\Program Files (x86)\\IDM\\IDMan.exe"
    assert program_of('""C:\\x\\y.exe"" -background') == "C:\\x\\y.exe"
    assert program_of("") == ""


def test_scan_lists_registry_folder_and_tasks(tmp_path):
    m, reg, folder = mgr(tmp_path, tasks=[{"name": "T1", "path": "\\", "enabled": False, "command": "wscript.exe x.vbs"}])
    reg.vals[("HKCU", startup.RUN.lower())] = {"Alpha": "C:\\a.exe", "Beta": "C:\\b.exe"}
    reg.vals[("HKLM", startup.RUNONCE.lower())] = {"Once": "C:\\once.exe"}
    reg.bins[("HKCU", f"{APPROVED}\\Run".lower(), "Beta")] = disabled_flag()
    (folder / "Tool.lnk").write_text("x")
    (folder / "desktop.ini").write_text("x")

    by = {e.name: e for e in m.scan()}
    assert set(by) == {"Alpha", "Beta", "Once", "Tool.lnk", "T1"}
    assert by["Alpha"].enabled and not by["Beta"].enabled
    assert by["Once"].can_toggle is False and by["Once"].scope == "machine"
    assert by["Tool.lnk"].kind == "folder" and by["T1"].kind == "task" and by["T1"].enabled is False
    assert len({e.id for e in by.values()}) == 5
    # the public form never leaks registry or file locations used for resolution
    assert "hive" not in by["Alpha"].public() and "path" not in by["Tool.lnk"].public()


def test_single_task_object_from_powershell_is_accepted(tmp_path):
    one = {"name": "Solo", "path": "\\Vendor\\", "enabled": True, "command": "x.exe"}
    m, *_ = mgr(tmp_path, tasks=one)
    assert [e.name for e in m.scan() if e.kind == "task"] == ["Solo"]


def test_bad_powershell_output_is_ignored(tmp_path):
    m, *_ = mgr(tmp_path, run=lambda cmd, **kw: Result(0, "garbage"))
    assert m.scan() == []
    m2, *_ = mgr(tmp_path, run=lambda cmd, **kw: Result(1, "boom"))
    assert m2.scan() == []


def test_disable_then_enable_registry_entry(tmp_path):
    m, reg, _ = mgr(tmp_path)
    reg.vals[("HKCU", startup.RUN.lower())] = {"Alpha": "C:\\a.exe"}
    eid = m.scan()[0].id
    assert m.set_enabled(eid, False) == {"ok": True}
    assert is_disabled(reg.bins[("HKCU", f"{APPROVED}\\Run".lower(), "Alpha")])
    assert m.scan()[0].enabled is False
    assert m.set_enabled(eid, True) == {"ok": True}
    assert m.scan()[0].enabled is True
    # the Run value itself is never touched by toggling
    assert reg.vals[("HKCU", startup.RUN.lower())] == {"Alpha": "C:\\a.exe"}


def test_wow64_entries_use_run32_approval(tmp_path):
    m, reg, _ = mgr(tmp_path)
    reg.vals[("HKLM", startup.RUN32.lower())] = {"Old": "C:\\old.exe"}
    m.set_enabled(m.scan()[0].id, False)
    assert ("HKLM", f"{APPROVED}\\Run32".lower(), "Old") in reg.bins


def test_runonce_cannot_be_toggled_but_can_be_deleted(tmp_path):
    m, reg, _ = mgr(tmp_path)
    reg.vals[("HKCU", startup.RUNONCE.lower())] = {"Once": "C:\\o.exe"}
    eid = m.scan()[0].id
    assert m.set_enabled(eid, False) == {"ok": False, "error": "cannot_toggle"}
    assert m.delete(eid) == {"ok": True}
    assert m.scan() == []


def test_delete_registry_entry_also_clears_approval(tmp_path):
    m, reg, _ = mgr(tmp_path)
    reg.vals[("HKCU", startup.RUN.lower())] = {"Alpha": "C:\\a.exe", "Keep": "C:\\k.exe"}
    reg.bins[("HKCU", f"{APPROVED}\\Run".lower(), "Alpha")] = disabled_flag()
    alpha = next(e for e in m.scan() if e.name == "Alpha")
    assert m.delete(alpha.id) == {"ok": True}
    assert [e.name for e in m.scan()] == ["Keep"]
    assert not any(k[2] == "Alpha" for k in reg.bins)


def test_folder_entry_toggle_and_delete(tmp_path):
    m, reg, folder = mgr(tmp_path)
    f = folder / "Tool.lnk"
    f.write_text("x")
    eid = m.scan()[0].id
    m.set_enabled(eid, False)
    assert ("HKCU", f"{APPROVED}\\StartupFolder".lower(), "Tool.lnk") in reg.bins
    assert m.delete(eid) == {"ok": True}
    assert not f.exists() and m.scan() == []


def test_machine_entries_report_admin_when_denied(tmp_path):
    m, reg, _ = mgr(tmp_path)
    reg.vals[("HKLM", startup.RUN.lower())] = {"Sys": "C:\\s.exe"}
    reg.readonly.add("HKLM")
    eid = m.scan()[0].id
    assert m.set_enabled(eid, False) == {"ok": False, "error": "admin"}
    assert m.delete(eid) == {"ok": False, "error": "admin"}
    assert m.scan()[0].enabled is True and len(m.scan()) == 1


def test_task_actions_use_environment_not_script_text(tmp_path):
    seen = []
    task = {"name": "Evil'; calc; '", "path": "\\", "enabled": True, "command": "x.exe"}

    def run(cmd, **kw):
        if "KS_TASK_ACTION" in (kw.get("env") or {}):
            seen.append((cmd, kw["env"]))
            return Result(0, "")
        return Result(0, json.dumps([task]))

    m, *_ = mgr(tmp_path, run=run)
    eid = m.scan()[0].id
    assert m.set_enabled(eid, False) == {"ok": True}
    assert m.delete(eid) == {"ok": True}
    assert [e["KS_TASK_ACTION"] for _, e in seen] == ["disable", "delete"]
    assert all(e["KS_TASK_NAME"] == task["name"] for _, e in seen)
    assert all(task["name"] not in " ".join(cmd) for cmd, _ in seen)


def test_task_access_denied_maps_to_admin(tmp_path):
    task = {"name": "T", "path": "\\", "enabled": True, "command": "x.exe"}

    def run(cmd, **kw):
        if "KS_TASK_ACTION" in (kw.get("env") or {}):
            return Result(1, "Disable-ScheduledTask : Access is denied.")
        return Result(0, json.dumps([task]))

    m, *_ = mgr(tmp_path, run=run)
    assert m.set_enabled(m.scan()[0].id, False) == {"ok": False, "error": "admin"}


def test_unknown_id_is_rejected(tmp_path):
    m, *_ = mgr(tmp_path)
    assert m.set_enabled("../../etc/passwd", True) == {"ok": False, "error": "not_found"}
    assert m.delete("C:\\Windows\\notepad.exe") == {"ok": False, "error": "not_found"}


def test_non_windows_is_empty_and_inert(tmp_path):
    m = StartupManager(host("linux"), reg=FakeStartupRegistry())
    assert m.scan() == []
    assert m.set_enabled("x", True)["ok"] is False and m.delete("x")["ok"] is False


def test_api_surface_and_non_windows(tmp_path, monkeypatch, fake_home):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    assert {"startup_list", "startup_set_enabled", "startup_delete"} <= set(PUBLIC)
    api = Api(Store(tmp_path / "cfg" / "keystone.json"))
    api.info = host("linux")
    assert api.startup_list()["supported"] is False
    assert api.startup_list()["entries"] == []


def test_admin_flags_for_registry_folder_and_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("USERNAME", "me")
    tasks = [
        {"name": "Mine", "path": "\\", "enabled": True, "command": "x.exe", "user": "PC\\me", "highest": False},
        {"name": "Sys", "path": "\\", "enabled": True, "command": "x.exe", "user": "SYSTEM", "highest": False},
        {"name": "Elev", "path": "\\", "enabled": True, "command": "x.exe", "user": "PC\\me", "highest": True},
    ]
    m, reg, _ = mgr(tmp_path, tasks=tasks)
    reg.vals[("HKCU", startup.RUN.lower())] = {"U": "C:/u.exe"}
    reg.vals[("HKLM", startup.RUN.lower())] = {"M": "C:/m.exe"}
    by = {e.name: e for e in m.scan()}
    assert not by["U"].needs_admin and by["M"].needs_admin
    assert not by["Mine"].needs_admin and by["Sys"].needs_admin and by["Elev"].needs_admin
    assert by["Elev"].runs_elevated and not by["Mine"].runs_elevated
    assert by["Elev"].public()["runs_elevated"] is True


def test_run_as_admin_compat_layer_is_detected(tmp_path):
    m, reg, _ = mgr(tmp_path)
    reg.vals[("HKCU", startup.RUN.lower())] = {"A": '"C:/Tools/a.exe" -x', "B": "C:/Tools/b.exe"}
    reg.vals[("HKCU", startup.LAYERS.lower())] = {"C:/Tools/a.exe": "~ RUNASADMIN", "C:/Tools/b.exe": "~ WIN7RTM"}
    by = {e.name: e for e in m.scan()}
    assert by["A"].runs_elevated and not by["B"].runs_elevated


def test_icons_only_for_known_ids_and_paths_via_environment(tmp_path):
    calls = []
    exe = tmp_path / "app.exe"
    exe.write_text("x")

    def run(cmd, **kw):
        env = kw.get("env") or {}
        if "KS_ICON_PATHS" in env:
            calls.append((cmd, json.loads(env["KS_ICON_PATHS"])))
            return Result(0, json.dumps({str(exe): "QUJD"}))
        return Result(0, "[]")

    m, reg, _ = mgr(tmp_path, run=run)
    reg.vals[("HKCU", startup.RUN.lower())] = {"App": str(exe), "Gone": "C:/definitely/missing.exe"}
    by = {e.name: e for e in m.scan()}
    got = m.icons([by["App"].id, by["Gone"].id, "../../evil"])
    assert got == {by["App"].id: "data:image/png;base64,QUJD"}
    assert calls[0][1] == [str(exe)] and str(exe) not in " ".join(calls[0][0])
    m.icons([by["App"].id])          # served from cache, no second PowerShell call
    assert len(calls) == 1


def test_icons_survive_bad_powershell_output(tmp_path):
    exe = tmp_path / "app.exe"
    exe.write_text("x")
    m, reg, _ = mgr(tmp_path, run=lambda cmd, **kw: Result(0, "garbage") if "KS_ICON_PATHS" in (kw.get("env") or {}) else Result(0, "[]"))
    reg.vals[("HKCU", startup.RUN.lower())] = {"App": str(exe)}
    eid = m.scan()[0].id
    assert m.icons([eid]) == {}


def test_api_exposes_startup_icons():
    assert "startup_icons" in PUBLIC
