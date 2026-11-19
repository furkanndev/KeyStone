"""Services, logon points, signatures, snapshots, reveal and VirusTotal for the start-up tab."""
import io
import json
import urllib.error

import pytest

from keystone.api import PUBLIC, Api
from keystone.core.proc import Result
from keystone.startup import (SERVICES, StartupManager, classify, program_of, resolve_payload)
from keystone.startup import manager as mgrmod
from keystone.startup.vt import VirusTotal
from keystone.store import Store
from tests.conftest import host
from tests.test_startup import FakeStartupRegistry

SVC = SERVICES


def make(tmp_path, reg=None, run=None, is_admin=False, **kw):
    reg = reg or FakeStartupRegistry()
    info = host("windows")
    info.is_admin = is_admin
    (tmp_path / "Startup").mkdir(exist_ok=True)
    m = StartupManager(info, reg=reg, run=run or (lambda cmd, **k: Result(0, "[]")),
                       folders=[(str(tmp_path / "Startup"), "user", "HKCU")], data_dir=tmp_path / "data",
                       indirect=lambda s: "Resolved " + s[-3:], **kw)
    return m, reg


def add_service(reg, name, start=2, typ=16, image=None, **extra):
    reg.put("HKLM", f"{SVC}\\{name}", Type=typ, Start=start, ImagePath=image or rf"C:\Vendor\{name}.exe", **extra)


# ------------------------------------------------------------------ payload resolution

@pytest.mark.parametrize("cmd,path", [
    (r"rundll32.exe C:\Vendor\x.dll,Run /s", r"C:\Vendor\x.dll"),
    (r'rundll32.exe "C:\Vendor Dir\x.dll",Run', r"C:\Vendor Dir\x.dll"),
    (r"regsvr32.exe /s C:\Vendor\y.dll", r"C:\Vendor\y.dll"),
    (r'wscript.exe "C:\a\start.vbs" //B', r"C:\a\start.vbs"),
    (r"cmd.exe /c C:\tools\go.cmd arg", r"C:\tools\go.cmd"),
    (r"powershell.exe -NoProfile -File C:\s\run.ps1", r"C:\s\run.ps1"),
])
def test_generic_hosts_resolve_to_their_payload(cmd, path):
    p = resolve_payload(cmd)
    assert p.generic and p.resolved and p.path == path and p.inspectable


@pytest.mark.parametrize("cmd", [r"powershell.exe -Command Do-Stuff", r"cmd.exe /c echo hi", "msiexec.exe /fu {GUID}",
                                 "mshta.exe http://x.example/a.hta", "wscript.exe"])
def test_unresolvable_generic_hosts_are_never_judged(cmd):
    p = resolve_payload(cmd)
    assert p.generic and not p.resolved and not p.inspectable


def test_first_program_wins_when_arguments_end_in_extensions():
    cmd = r"C:\WINDOWS\system32\cmd.exe /d /c C:\WINDOWS\system32\task.cmd"
    assert program_of(cmd) == r"C:\WINDOWS\system32\cmd.exe"


def test_plain_programs_are_their_own_payload():
    p = resolve_payload(r'"C:\Program Files\KeePassXC\KeePassXC.exe" --tray')
    assert not p.generic and p.path == r"C:\Program Files\KeePassXC\KeePassXC.exe" and p.inspectable


# ------------------------------------------------------------------ signatures

def test_microsoft_means_valid_signature_with_microsoft_organisation():
    ms = classify({"status": "Valid", "publisher": "Microsoft Windows", "subject": "CN=Microsoft Windows, O=Microsoft Corporation, L=Redmond"})
    assert ms["microsoft"] and ms["signature"] == "valid"
    spoof = classify({"status": "Valid", "publisher": "Microsoft Corp", "subject": "CN=Microsoft Corp, O=Evil Microsoft Corporation Ltd"})
    assert not spoof["microsoft"]
    bad = classify({"status": "HashMismatch", "publisher": "Microsoft Windows", "subject": "O=Microsoft Corporation"})
    assert bad["signature"] == "invalid" and not bad["microsoft"]
    assert classify({"status": "NotSigned"})["signature"] == "unsigned"
    assert classify({"status": "Missing"})["signature"] == "missing"


def test_inspect_judges_the_payload_and_caches_by_file(tmp_path):
    dll = tmp_path / "x.dll"
    dll.write_text("x")
    calls = []

    def run(cmd, **kw):
        env = kw.get("env") or {}
        if "KS_PATHS" in env:
            paths = json.loads(env["KS_PATHS"])
            calls.append(paths)
            return Result(0, json.dumps({p: {"target": p, "status": "Valid", "publisher": "Vendor Ltd",
                                              "subject": "O=Vendor Ltd"} for p in paths}))
        return Result(0, "[]")

    m, reg = make(tmp_path, run=run, cache_file=tmp_path / "cache.json")
    reg.put("HKCU", mgrmod.RUN, Vendor=rf"rundll32.exe {dll},Run", Plain=str(dll))
    ids = [e.id for e in m.scan()]
    got = m.inspect(ids)
    assert len(got) == 2 and all(v["publisher"] == "Vendor Ltd" and not v["microsoft"] for v in got.values())
    assert calls == [[str(dll)]]                                    # host rundll32 is never inspected; one batched call
    m.inspect(ids)
    assert len(calls) == 1                                           # cached by path, mtime and size
    m2, reg2 = make(tmp_path, run=run, cache_file=tmp_path / "cache.json")
    reg2.put("HKCU", mgrmod.RUN, Plain=str(dll))
    m2.inspect([e.id for e in m2.scan()])
    assert len(calls) == 1                                           # persisted cache survives a new manager
    dll.write_text("changed content")
    m.inspect(ids)
    assert len(calls) == 2                                           # a changed file is inspected again


def test_unresolved_payload_stays_unknown(tmp_path):
    m, reg = make(tmp_path)
    reg.put("HKCU", mgrmod.RUN, Script="powershell.exe -Command Do-Stuff")
    e = m.scan()[0]
    assert e.target == "" and m.inspect([e.id]) == {}


def test_shortcut_target_is_resolved_then_judged(tmp_path):
    exe = tmp_path / "app.exe"
    exe.write_text("x")
    lnk = tmp_path / "Startup" / "App.lnk"
    seen = []

    def run(cmd, **kw):
        env = kw.get("env") or {}
        if "KS_PATHS" in env:
            paths = json.loads(env["KS_PATHS"])
            seen.append(paths)
            if paths == [str(lnk)]:
                return Result(0, json.dumps({str(lnk): str(exe)}))
            return Result(0, json.dumps({p: {"target": p, "status": "NotSigned"} for p in paths}))
        return Result(0, "[]")

    m, _ = make(tmp_path, run=run)
    lnk.parent.mkdir(exist_ok=True)
    lnk.write_text("lnk")
    e = next(x for x in m.scan() if x.kind == "folder")
    got = m.inspect([e.id])
    assert got[e.id]["signature"] == "unsigned"
    assert seen == [[str(lnk)], [str(exe)]]


# ------------------------------------------------------------------ services

def test_services_listing_filters_and_resolves(tmp_path):
    m, reg = make(tmp_path)
    add_service(reg, "AutoSvc", 2, 16, DisplayName="@%SystemRoot%\\x.dll,-101", Description="plain text")
    add_service(reg, "Delayed", 2, 32, DelayedAutostart=1)
    add_service(reg, "Off", 4, 16)
    add_service(reg, "Manual", 3, 16)
    add_service(reg, "Driver", 2, 1)
    add_service(reg, "UserTemplate", 2, 224)
    reg.put("HKLM", f"{SVC}\\NoImage", Type=16, Start=2)
    by = {e.service: e for e in m.scan() if e.kind == "service"}
    assert set(by) == {"AutoSvc", "Delayed", "Off"}
    assert by["AutoSvc"].name == "Resolved 101" and by["AutoSvc"].description == "plain text"
    assert by["AutoSvc"].start == "auto" and by["Off"].start == "disabled" and not by["Off"].enabled
    assert by["Delayed"].delayed and by["Delayed"].start == "auto"
    assert by["AutoSvc"].needs_admin and by["AutoSvc"].id.startswith("svc-")


def test_svchost_services_use_their_service_dll(tmp_path):
    m, reg = make(tmp_path)
    add_service(reg, "Hosted", 2, 32, image=r"C:\WINDOWS\system32\svchost.exe -k netsvcs -p")
    reg.put("HKLM", f"{SVC}\\Hosted\\Parameters", ServiceDll=r"C:\Vendor\hosted.dll")
    add_service(reg, "Locked", 2, 32, image=r"C:\WINDOWS\system32\svchost.exe -k other")     # Parameters unreadable
    by = {e.service: e for e in m.scan() if e.kind == "service"}
    assert by["Hosted"].target == r"C:\Vendor\hosted.dll"
    assert by["Locked"].target == ""        # unknown: stays visible, never assumed to be Microsoft's


def test_critical_and_required_services_are_protected(tmp_path):
    m, reg = make(tmp_path)
    add_service(reg, "RpcSs", 2)
    add_service(reg, "Base", 2)
    add_service(reg, "Needy", 2, DependOnService=["Base", "+Group"])
    add_service(reg, "Lonely", 2)
    by = {e.service: e for e in m.scan() if e.kind == "service"}
    assert by["RpcSs"].protected == "critical"
    assert by["Base"].protected == "dependency"
    assert by["Needy"].protected == "" and by["Lonely"].protected == ""


def test_set_start_runs_sc_with_arguments_and_remembers_the_original(tmp_path):
    calls = []

    def run(cmd, **kw):
        if cmd[0] == "sc.exe":
            calls.append(cmd)
            return Result(0, "")
        return Result(0, "[]")

    m, reg = make(tmp_path, run=run, is_admin=True)
    add_service(reg, "Vendor Svc", 2, DelayedAutostart=1)
    sid = next(e.id for e in m.scan() if e.kind == "service")
    assert m.set_start(sid, "manual") == {"ok": True}
    assert calls[-1] == ["sc.exe", "config", "Vendor Svc", "start=", "demand"]
    assert json.loads((tmp_path / "data" / "startup_services.json").read_text())["Vendor Svc"] == {"start": 2, "delayed": True}
    assert m.set_start(sid, "disabled") == {"ok": True}
    assert calls[-1][-1] == "disabled"
    reg.put("HKLM", f"{SVC}\\Vendor Svc", Start=4)           # what sc would have written
    assert m.set_start(sid, "auto") == {"ok": True}
    assert calls[-1][-1] == "delayed-auto"                    # delayed start is restored, not lost
    assert not (tmp_path / "data" / "startup_services.json").read_text().count("Vendor")


def test_service_changed_to_manual_stays_listed_so_it_can_be_reverted(tmp_path):
    m, reg = make(tmp_path, run=lambda cmd, **k: Result(0, "[]"), is_admin=True)
    add_service(reg, "Vendor", 2)
    sid = next(e.id for e in m.scan() if e.kind == "service")
    m.set_start(sid, "manual")
    reg.put("HKLM", f"{SVC}\\Vendor", Start=3)
    again = [e for e in m.scan() if e.kind == "service"]
    assert len(again) == 1 and again[0].start == "manual"


def test_protected_services_are_refused_on_the_server(tmp_path):
    calls = []
    m, reg = make(tmp_path, run=lambda cmd, **k: calls.append(cmd) or Result(0, "[]"))
    add_service(reg, "RpcSs", 2)
    sid = next(e.id for e in m.scan() if e.kind == "service")
    assert m.set_start(sid, "disabled") == {"ok": False, "error": "protected", "reason": "critical"}
    assert m.set_start(sid, "manual")["error"] == "protected"
    assert not any(c[0] == "sc.exe" for c in calls)


def test_access_denied_differs_for_standard_users_and_admins(tmp_path):
    def run(cmd, **kw):
        return Result(5, "Access is denied.") if cmd[0] == "sc.exe" else Result(0, "[]")

    m, reg = make(tmp_path, run=run, is_admin=False)
    add_service(reg, "Vendor", 2)
    sid = next(e.id for e in m.scan() if e.kind == "service")
    assert m.set_start(sid, "disabled") == {"ok": False, "error": "admin"}
    m.info.is_admin = True
    assert m.set_start(sid, "disabled") == {"ok": False, "error": "protected", "reason": "system"}


def test_service_start_type_validation_and_no_delete(tmp_path):
    m, reg = make(tmp_path, is_admin=True)
    add_service(reg, "Vendor", 2)
    sid = next(e.id for e in m.scan() if e.kind == "service")
    assert m.set_start(sid, "boot")["error"] == "bad_mode"
    assert m.delete(sid) == {"ok": False, "error": "readonly"}
    assert m.set_enabled(sid, False) == {"ok": False, "error": "readonly"}
    reg.put("HKCU", mgrmod.RUN, Alpha=r"C:\a.exe")
    rid = next(e.id for e in m.scan() if e.kind == "registry")
    assert m.set_start(rid, "manual")["error"] == "readonly"


# ------------------------------------------------------------------ logon points

def test_logon_points_are_listed_flagged_and_read_only(tmp_path):
    m, reg = make(tmp_path)
    reg.put("HKLM", mgrmod.WINLOGON, Shell="explorer.exe,evil.exe", Userinit=r"C:\Windows\system32\userinit.exe,")
    reg.put("HKLM", mgrmod.APPINIT[0], AppInit_DLLs=r"C:\evil\hook.dll", LoadAppInit_DLLs=1)
    reg.put("HKLM", mgrmod.IFEO[0] + r"\notepad.exe", Debugger=r"C:\tools\dbg.exe")
    reg.put("HKLM", mgrmod.IFEO[0] + r"\calc.exe", GlobalFlag=2)
    reg.put("HKLM", mgrmod.ACTIVE_SETUP[0] + r"\{GUID-1}", StubPath=r"C:\v\setup.exe /x")
    by = {e.name: e for e in m.scan() if e.kind == "logon"}
    assert by["Winlogon · Shell"].suspicious                      # changed from "explorer.exe"
    assert not by["Winlogon · Userinit"].suspicious               # default value, trailing comma included
    assert by["AppInit_DLLs"].suspicious and "LoadAppInit_DLLs = 1" in by["AppInit_DLLs"].note
    assert by["notepad.exe · Debugger"].suspicious and "calc.exe · Debugger" not in by
    assert by["Active Setup · {GUID-1}"].readonly and not by["Active Setup · {GUID-1}"].suspicious
    e = by["Winlogon · Shell"]
    assert not e.can_toggle and e.readonly
    assert m.set_enabled(e.id, False) == {"ok": False, "error": "readonly"}
    assert m.delete(e.id) == {"ok": False, "error": "readonly"}


def test_modified_userinit_is_flagged(tmp_path):
    m, reg = make(tmp_path)
    reg.put("HKLM", mgrmod.WINLOGON, Userinit=r"C:\Windows\system32\userinit.exe,C:\evil.exe")
    e = next(x for x in m.scan() if x.kind == "logon")
    assert e.suspicious


# ------------------------------------------------------------------ scheduled tasks via COM class

def test_com_task_actions_resolve_through_the_class_server(tmp_path):
    dll = r"C:\Windows\System32\thing.dll"
    task = {"name": "ComTask", "path": "\\Microsoft\\Windows\\X\\", "enabled": True, "command": "", "clsid": "{ABC}",
            "user": "SYSTEM", "highest": False}
    m, reg = make(tmp_path, run=lambda cmd, **k: Result(0, json.dumps([task])))
    reg.put("HKLM", r"SOFTWARE\Classes\CLSID\{ABC}\InprocServer32", **{"": dll})
    e = next(x for x in m.scan() if x.kind == "task")
    assert e.command == "COM {ABC}" and e.target == dll


def test_actions_only_scan_the_kind_of_the_id(tmp_path):
    ps_calls = []

    def run(cmd, **kw):
        ps_calls.append(cmd)
        return Result(0, "[]")

    m, reg = make(tmp_path, run=run)
    reg.put("HKCU", mgrmod.RUN, Alpha=r"C:\a.exe")
    rid = next(e.id for e in m.scan() if e.kind == "registry")
    ps_calls.clear()
    assert m.set_enabled(rid, False) == {"ok": True}
    assert ps_calls == []                    # no scheduled-task query, no service sweep for a registry entry
    assert m.set_enabled("tsk-nope", True)["error"] == "not_found"
    assert m.set_enabled("whatever", True)["error"] == "not_found"


# ------------------------------------------------------------------ snapshots

def test_without_a_snapshot_nothing_is_flagged_new(tmp_path):
    m, reg = make(tmp_path)
    reg.put("HKCU", mgrmod.RUN, Alpha=r"C:\a.exe")
    out = m.list_public()
    assert out["snapshot"] == {"has": False, "time": "", "count": 0, "added": [], "changed": [], "removed": []}


def test_snapshot_reports_added_changed_and_removed(tmp_path):
    m, reg = make(tmp_path)
    add_service(reg, "Svc", 2)
    reg.put("HKCU", mgrmod.RUN, Keep=r"C:\k.exe", Gone=r"C:\g.exe", Edit=r"C:\e.exe")
    saved = m.save_snapshot("before")
    assert saved["ok"] and saved["count"] == 4
    reg.vals[("HKCU", mgrmod.RUN.lower())] = {"Keep": r"C:\k.exe", "Edit": r"C:\e2.exe", "New": r"C:\n.exe"}
    reg.put("HKLM", f"{SVC}\\Svc", Start=4)
    out = m.list_public()
    snap = out["snapshot"]
    names = {e["id"]: e["name"] for e in out["entries"]}
    assert snap["has"] and snap["count"] == 4
    assert [names[i] for i in snap["added"]] == ["New"]
    assert sorted(names[i] for i in snap["changed"]) == ["Edit", "Svc"]
    assert [r["name"] for r in snap["removed"]] == ["Gone"]


def test_snapshot_needs_storage(tmp_path):
    info = host("windows")
    m = StartupManager(info, reg=FakeStartupRegistry(), run=lambda c, **k: Result(0, "[]"), folders=[])
    assert m.save_snapshot()["ok"] is False


# ------------------------------------------------------------------ reveal

def test_reveal_file_and_registry(tmp_path):
    exe = tmp_path / "app.exe"
    exe.write_text("x")
    spawned, opened = [], []
    m, reg = make(tmp_path, spawn=spawned.append, shell_open=opened.append)
    reg.put("HKLM", mgrmod.RUN, App=str(exe))
    e = next(x for x in m.scan() if x.kind == "registry")
    assert m.reveal(e.id, "file") == {"ok": True}
    assert spawned == [["explorer.exe", "/select,", str(exe)]]         # path as its own argument: spaces are safe
    assert m.reveal(e.id, "registry") == {"ok": True}
    assert opened == ["regedit.exe"]
    last = reg.get_value("HKCU", mgrmod.REGEDIT_STATE, "LastKey")
    assert last == "Computer\\HKEY_LOCAL_MACHINE\\" + mgrmod.RUN
    assert m.reveal("reg-unknown", "file")["error"] == "not_found"


def test_reveal_refuses_missing_files(tmp_path):
    spawned = []
    m, reg = make(tmp_path, spawn=spawned.append)
    reg.put("HKCU", mgrmod.RUN, Ghost=r"C:\definitely\missing.exe")
    e = m.scan()[0]
    assert m.reveal(e.id, "file") == {"ok": False, "error": "no_file"} and spawned == []


# ------------------------------------------------------------------ VirusTotal

class FakeResp:
    def __init__(self, body):
        self._b = json.dumps(body).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(b"{}"))


def vt_setup(tmp_path, opener):
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"hello")
    m, reg = make(tmp_path, opener=opener)
    reg.put("HKCU", mgrmod.RUN, App=str(exe))
    return m, next(e.id for e in m.scan() if e.kind == "registry")


SHA_HELLO = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_vt_link_is_computed_locally_without_any_request(tmp_path):
    def boom(*a, **k):
        raise AssertionError("network used")

    m, eid = vt_setup(tmp_path, boom)
    assert m.vt_url(eid) == {"ok": True, "sha256": SHA_HELLO, "url": "https://www.virustotal.com/gui/file/" + SHA_HELLO}


def test_vt_lookup_needs_opt_in_and_a_key(tmp_path):
    def boom(*a, **k):
        raise AssertionError("network used")

    m, eid = vt_setup(tmp_path, boom)
    assert m.vt_lookup(eid, False, "key")["error"] == "disabled"
    assert m.vt_lookup(eid, True, "")["error"] == "no_key"


def test_vt_lookup_sends_only_the_hash_and_reads_the_stats(tmp_path):
    seen = []

    def opener(req, timeout=None):
        seen.append((req.full_url, req.get_header("X-apikey"), req.data, req.get_method()))
        return FakeResp({"data": {"attributes": {"last_analysis_stats": {
            "malicious": 2, "suspicious": 1, "undetected": 60, "harmless": 9, "timeout": 0}}}})

    m, eid = vt_setup(tmp_path, opener)
    r = m.vt_lookup(eid, True, "SECRET")
    assert r["ok"] and (r["malicious"], r["suspicious"], r["total"]) == (2, 1, 72)
    assert r["link"].endswith(SHA_HELLO)
    assert seen == [("https://www.virustotal.com/api/v3/files/" + SHA_HELLO, "SECRET", None, "GET")]
    assert "SECRET" not in json.dumps(r)


@pytest.mark.parametrize("code,error", [(404, "not_found"), (401, "bad_key"), (429, "rate_limit"), (500, "http_500")])
def test_vt_http_errors_map_to_small_codes(tmp_path, code, error):
    def opener(req, timeout=None):
        raise http_error(code)

    m, eid = vt_setup(tmp_path, opener)
    r = m.vt_lookup(eid, True, "K")
    assert r["ok"] is False and r["error"] == error and r["link"].endswith(SHA_HELLO)


def test_vt_network_failure_and_bad_json(tmp_path):
    m, eid = vt_setup(tmp_path, lambda req, timeout=None: (_ for _ in ()).throw(urllib.error.URLError("down")))
    assert m.vt_lookup(eid, True, "K")["error"] == "network"


@pytest.mark.parametrize("body", [
    {},
    {"data": {"attributes": {}}},
    {"data": {"attributes": {"last_analysis_stats": {}}}},
    {"data": {"attributes": {"last_analysis_stats": {"malicious": 0, "suspicious": 0, "harmless": 0, "undetected": 0}}}},
    {"data": {"attributes": {"last_analysis_stats": {"malicious": "x"}}}},
])
def test_vt_missing_or_empty_stats_is_never_reported_as_clean(tmp_path, body):
    m, eid = vt_setup(tmp_path, lambda req, timeout=None: FakeResp(body))
    r = m.vt_lookup(eid, True, "K")
    assert r["ok"] is False and r["error"] == "no_data" and r["link"].endswith(SHA_HELLO)


def test_explorer_is_the_shell_alone_or_a_launcher_for_its_argument():
    shell = resolve_payload("explorer.exe")
    assert not shell.generic and shell.inspectable and shell.path == "explorer.exe"
    launch = resolve_payload(r"explorer.exe C:\Docs\report.lnk")
    assert launch.generic and launch.path == r"C:\Docs\report.lnk"
    assert not resolve_payload("explorer.exe shell:startup").inspectable


def test_dll_paths_with_spaces_parse_as_one_program():
    assert program_of(r"C:\Program Files\Vendor Co\thing.dll") == r"C:\Program Files\Vendor Co\thing.dll"


def test_vt_calls_are_spaced_out_and_results_cached():
    now = [100.0]
    calls = []

    def opener(req, timeout=None):
        calls.append(req.full_url)
        return FakeResp({"data": {"attributes": {"last_analysis_stats": {"harmless": 5}}}})

    vt = VirusTotal(opener=opener, clock=lambda: now[0])
    assert vt.lookup("a" * 64, "K")["ok"]
    r = vt.lookup("b" * 64, "K")
    assert r["error"] == "rate_limit" and 1 <= r["retry_after"] <= 17
    now[0] += 20
    assert vt.lookup("b" * 64, "K")["ok"]
    assert vt.lookup("a" * 64, "K")["ok"] and len(calls) == 2       # cached, no third request


def test_vt_inspects_the_payload_not_the_generic_host(tmp_path):
    dll = tmp_path / "x.dll"
    dll.write_bytes(b"hello")
    m, reg = make(tmp_path, opener=lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network")))
    reg.put("HKCU", mgrmod.RUN, Via=rf"rundll32.exe {dll},Run", Bare="powershell.exe -Command x")
    by = {e.name: e for e in m.scan() if e.kind == "registry"}
    assert m.vt_url(by["Via"].id)["sha256"] == SHA_HELLO
    assert m.vt_url(by["Bare"].id) == {"ok": False, "error": "no_file"}


# ------------------------------------------------------------------ settings and API surface

def test_vt_key_never_reaches_the_interface(tmp_path, monkeypatch, fake_home):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    api = Api(Store(tmp_path / "cfg" / "keystone.json"))
    assert api.bootstrap()["settings"]["vt_key_set"] is False
    out = api.settings_set({"vt_api_key": "  SECRET  ", "vt_enabled": 1})
    assert out["vt_key_set"] is True and out["vt_enabled"] is True and "vt_api_key" not in out
    assert "SECRET" not in json.dumps(api.bootstrap())
    assert api.store.settings["vt_api_key"] == "SECRET"
    assert api.settings_set({"vt_api_key": ""})["vt_key_set"] is False


def test_vt_key_is_not_part_of_exported_profiles(tmp_path, monkeypatch, fake_home):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    api = Api(Store(tmp_path / "cfg" / "keystone.json"))
    api.settings_set({"vt_api_key": "SECRET"})
    p = api.store.active()
    out = api.store.export(p["id"], tmp_path / "p.ksprofile")
    assert "SECRET" not in out.read_text(encoding="utf-8")


def test_new_methods_are_whitelisted():
    for n in ("startup_inspect", "startup_set_start", "startup_snapshot_save", "startup_reveal", "startup_vt_url",
              "startup_vt_lookup"):
        assert n in PUBLIC


def test_api_vt_lookup_uses_the_stored_opt_in_and_key(tmp_path, monkeypatch, fake_home):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    api = Api(Store(tmp_path / "cfg" / "keystone.json"))
    api.info = host("linux")
    assert api._startup().vt_lookup("reg-x", False, "")["error"] == "disabled"
    assert api.startup_vt_lookup("reg-x")["error"] == "disabled"      # off by default
