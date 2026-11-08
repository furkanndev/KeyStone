import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from keystone.api import PUBLIC, Api
from keystone.server import make_server
from keystone.store import Store


@pytest.fixture
def api(tmp_path, monkeypatch, fake_home):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    return Api(Store(tmp_path / "cfg" / "keystone.json"))


def test_store_migrates_legacy_profiles(tmp_path, monkeypatch):
    legacy = tmp_path / "appdata" / "Keystone"
    legacy.mkdir(parents=True)
    (legacy / "profiles.json").write_text(json.dumps({
        "active_profile_id": "prof_x", "theme": "light", "language": "en",
        "profiles": [{"id": "prof_x", "name": "Gaming", "apps": ["steam"], "tweaks": ["dark_mode"],
                      "backups": ["vscode", "dev_environment", "winget_manifest"]}]}))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    s = Store(tmp_path / "new.json")
    p = s.active()
    assert p["name"] == "Gaming" and p["apps"] == ["steam"]
    assert p["backup"] == ["editors", "git_ssh", "shell", "env", "apps"]
    assert s.settings["lang"] == "en" and s.settings["theme"] == "light"


def test_profiles_crud_and_export(tmp_path, api):
    p = api.profile_create("Dev")
    api.profile_update(p["id"], {"apps": ["git", "vscode"]})
    assert api.store.active()["apps"] == ["git", "vscode"]
    api.store.export(p["id"], tmp_path / "dev.ksprofile")
    q = api.store.import_(tmp_path / "dev.ksprofile")
    assert q["apps"] == ["git", "vscode"] and q["id"] != p["id"]
    api.profile_delete(q["id"])
    assert len(api.store.profiles()) == 2


def test_profile_custom_apps_isolation(api):
    p1 = api.store.active()
    res1 = api.add_github_app("furkanndev/Enclave", name="Enclave", desc="Enclave tool", category="github", icon_url="data:image/png;base64,iVBORw0KGgo=", pid=p1["id"])
    assert res1["ok"] is True
    assert any(x["id"] == "gh_furkanndev_enclave" for x in api.store.custom_apps(p1["id"]))
    assert "gh_furkanndev_enclave" in p1["apps"]

    p2 = api.profile_create("Dev Profile")
    assert api.store.custom_apps(p2["id"]) == []
    assert "gh_furkanndev_enclave" not in p2["apps"]

    cat2 = api.get_catalog()
    assert not any(p["id"] == "gh_furkanndev_enclave" for p in cat2["packages"])

    res2 = api.add_github_app("deskflow/deskflow", name="Deskflow Custom", desc="Deskflow tool", category="github", icon_url="data:image/png;base64,iVBORw0KGgo=", pid=p2["id"])
    assert res2["ok"] is True
    assert any(x["id"] == "gh_deskflow_deskflow" for x in api.store.custom_apps(p2["id"]))
    assert not any(x["id"] == "gh_deskflow_deskflow" for x in api.store.custom_apps(p1["id"]))

    api.profile_activate(p1["id"])
    cat1 = api.get_catalog()
    cat1_ids = [p["id"] for p in cat1["packages"]]
    assert "gh_furkanndev_enclave" in cat1_ids
    assert "gh_deskflow_deskflow" not in cat1_ids


def test_profile_export_import_with_custom_apps(tmp_path, api):
    p = api.profile_create("Design")
    api.add_github_app("furkanndev/Enclave", name="Enclave", desc="Enc", category="github", icon_url="data:image/png;base64,iVBORw0KGgo=", pid=p["id"])

    exp_file = tmp_path / "design.ksprofile"
    api.store.export(p["id"], exp_file)

    imported = api.store.import_(exp_file)
    assert any(x["id"] == "gh_furkanndev_enclave" for x in imported["custom_apps"])
    assert "gh_furkanndev_enclave" in imported["apps"]


def test_export_script_linux(api, monkeypatch):
    from keystone.core.system import SystemInfo
    from keystone.pkg.registry import ALL
    monkeypatch.setattr(api, "info", SystemInfo("linux", "Ubuntu 24.04", "24.04", "x64", distro_id="ubuntu"))
    monkeypatch.setattr(api, "_managers", lambda: {"apt": ALL["apt"](), "flatpak": ALL["flatpak"]()})
    s = api.export_script(["git", "vlc", "chrome", "directx"])
    assert "sudo apt-get install -y git vlc" in s["text"]
    assert "flatpak install --user -y flathub com.google.Chrome" in s["text"]
    assert "# directx: not available" in s["text"]


def test_server_auth_and_calls(api):
    httpd, token = make_server(api, 0, token="T0K")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    base = f"http://127.0.0.1:{port}"
    try:
        assert urllib.request.urlopen(base + "/").status == 200

        def call(name, *args, tok="T0K", host=None):
            req = urllib.request.Request(f"{base}/api/{name}", data=json.dumps({"args": list(args)}).encode(),
                                         headers={"X-KeyStone-Token": tok, "Content-Type": "application/json",
                                                  **({"Host": host} if host else {})})
            return json.loads(urllib.request.urlopen(req).read())

        boot = call("bootstrap")["result"]
        assert boot["system"]["os"] in ("linux", "macos", "windows") and boot["profiles"]
        with pytest.raises(urllib.error.HTTPError) as e:
            call("bootstrap", tok="bad")
        assert e.value.code == 401
        with pytest.raises(urllib.error.HTTPError) as e:
            call("bootstrap", host="evil.example")
        assert e.value.code == 403
        with pytest.raises(urllib.error.HTTPError) as e:
            call("__init__")
        assert e.value.code == 404
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/../keystone/api.py")
    finally:
        httpd.shutdown()


def test_backup_job_emits_events(api, tmp_path):
    events = []
    done = threading.Event()

    def on(ev):
        events.append(ev)
        if ev["type"] == "job" and ev["job"]["state"] in ("done", "failed"):
            done.set()
    api.subscribe(on)
    api.backup_start(["git_ssh", "fonts"], str(tmp_path / "bk"), "")
    assert done.wait(30)
    final = [e for e in events if e["type"] == "job"][-1]["job"]
    assert final["state"] == "done" and all(i["state"] == "done" for i in final["items"])
    assert final["result"]["path"].endswith(".ksbak")
    assert any(e["type"] == "log" for e in events)
    assert api.list_backups(str(tmp_path / "bk"))[0]["items"] == ["git_ssh", "fonts"]


def test_startup_steps_report_in_order(api, monkeypatch):
    from keystone.app import startup_steps

    def scan():
        api._installed = {"winget": {"git", "node"}}
        return {"scanning": False}

    monkeypatch.setattr(api, "scan", scan)
    seen = []
    summary = startup_steps(api, lambda step, state, detail="", values=None: seen.append((step, state, detail, values)), pace=0)
    assert [s for s, st, *_ in seen if st != "run"] == ["os", "managers", "rights", "catalog"]
    step, state, detail, values = seen[-1]
    assert (step, state, detail) == ("catalog", "done", "sp_fit")
    assert values["total"] - values["fit"] == summary["hidden"]


def test_startup_steps_stop_waiting_when_skipped(api, monkeypatch):
    from keystone.app import startup_steps

    api._scanning = True
    monkeypatch.setattr(api, "scan", lambda: {"scanning": True})
    skip = threading.Event()
    skip.set()
    start = time.monotonic()
    startup_steps(api, lambda *a: None, skip, scan_timeout=30, pace=0)
    assert time.monotonic() - start < 5


def test_startup_steps_do_not_wait_forever_for_scan(api, monkeypatch):
    from keystone.app import startup_steps

    api._scanning = True
    monkeypatch.setattr(api, "scan", lambda: {"scanning": True})
    start = time.monotonic()
    startup_steps(api, lambda *a: None, scan_timeout=0.05, pace=0)
    assert time.monotonic() - start < 5


def test_public_surface_is_whitelisted():
    assert "bootstrap" in PUBLIC and "install" in PUBLIC
    assert "set_lock_screen_timeout" in PUBLIC
    assert not any(n.startswith("_") for n in PUBLIC)


def test_relaunch_intent_roundtrip(tmp_path, monkeypatch):
    from keystone.core import proc
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    proc.record_relaunch_intent(view="tweaks", tweak="lock_screen_timeout_unhide")
    intent = proc.get_relaunch_intent()
    assert intent is not None
    assert intent["view"] == "tweaks"
    assert intent["tweak"] == "lock_screen_timeout_unhide"
    # Second read should be None as intent is consumed
    assert proc.get_relaunch_intent() is None


def test_api_bootstrap_carries_initial_view_and_target_tweak(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    custom_api = Api(Store(tmp_path / "cfg.json"), initial_view="tweaks", target_tweak="disable_uac_prompts")
    boot = custom_api.bootstrap()
    assert boot["initial_view"] == "tweaks"
    assert boot["target_tweak"] == "disable_uac_prompts"


def test_generate_bios_script(tmp_path, api):
    assert "generate_bios_script" in PUBLIC

    # 1. Direct destination path
    dest = tmp_path / "custom" / "reboot_bios.bat"
    res = api.generate_bios_script(dest_path=str(dest))
    assert res["ok"] is True
    assert res["saved"] is True
    assert dest.exists()
    content = dest.read_text(encoding="utf-8")
    assert "shutdown.exe /r /fw /t 2" in content
    assert "Start-Process" in content

    # 2. Native dialog mock
    class FakeDialogs:
        def save(self, name):
            return str(tmp_path / name)

    api.dialogs = FakeDialogs()
    res2 = api.generate_bios_script()
    assert res2["ok"] is True
    assert res2["saved"] is True
    assert (tmp_path / "BIOS_Yeniden_Baslat.bat").exists()

    # 3. Native dialog cancelled
    api.dialogs = type("CancelledDialogs", (), {"save": lambda self, name: None})()
    res3 = api.generate_bios_script()
    assert res3["ok"] is False
    assert res3.get("cancelled") is True

    # 4. Web browser fallback mode (no dialogs)
    api.dialogs = None
    res4 = api.generate_bios_script()
    assert res4["ok"] is True
    assert res4["saved"] is False
    assert "shutdown.exe /r /fw /t 2" in res4["content"]
