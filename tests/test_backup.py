import io
import os
import json
import stat
import zipfile
from pathlib import Path

import pytest

from keystone import backup
from keystone.backup import archive, crypto
from keystone.backup.items.wifi import parse_windows_xml, windows_xml
from keystone.core.proc import CancelToken

from .conftest import host

ITEMS = ["browsers", "editors", "git_ssh", "shell", "fonts"]


def test_crypto_roundtrip_and_tamper():
    data = b"x" * (crypto.CHUNK * 2 + 123)
    enc = io.BytesIO()
    crypto.encrypt_stream(io.BytesIO(data), enc, "s3cret")
    blob = enc.getvalue()
    out = io.BytesIO()
    crypto.decrypt_stream(io.BytesIO(blob), out, "s3cret")
    assert out.getvalue() == data
    with pytest.raises(crypto.BadPassword):
        crypto.decrypt_stream(io.BytesIO(blob), io.BytesIO(), "wrong")
    # Dropping the final chunk must be detected (no silent truncation).
    first_len = int.from_bytes(blob[32:36], "big")
    cut = blob[: 32 + 4 + first_len]
    with pytest.raises(ValueError):
        crypto.decrypt_stream(io.BytesIO(cut), io.BytesIO(), "s3cret")


def test_archive_rejects_path_traversal(tmp_path):
    evil = tmp_path / "evil.ksbak"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("manifest.json", "{}")
        zf.writestr("../../escape.txt", "boom")
    with pytest.raises(ValueError):
        archive.unpack(evil)
    assert not (tmp_path.parent / "escape.txt").exists()


def test_wifi_windows_xml_roundtrip():
    net = {"ssid": "Ev & <Ofis>", "auth": "psk", "key": "p@ss'\"word", "hidden": True}
    assert parse_windows_xml(windows_xml(net)) == net
    open_net = {"ssid": "Cafe", "auth": "open", "key": "", "hidden": False}
    assert parse_windows_xml(windows_xml(open_net)) == open_net


def test_detect_finds_everything(fake_home):
    found = {i["id"]: i["found"] for i in backup.detect_all(host())}
    assert found["browsers"]["count"] == 6
    assert "Firefox" in found["browsers"]["detail"]
    assert found["editors"]["detail"] == "Visual Studio Code"
    assert found["git_ssh"]["count"] == 3
    assert found["fonts"]["count"] == 1


def _run_backup(tmp_path, password=""):
    logs = []
    res = backup.backup(host(), ITEMS, tmp_path / "out", password or None, logs.append,
                        lambda *a: None, CancelToken(), "en")
    return Path(res["path"]), res, logs


def test_encrypted_backup_and_cross_machine_restore(fake_home, empty_home, tmp_path, monkeypatch):
    path, res, _ = _run_backup(tmp_path, "pw")
    assert all(v["ok"] for v in res["items"].values()), res["items"]
    assert crypto.is_encrypted(str(path))
    assert res["items"]["browsers"]["count"] == 8      # 3 + 3 chromium, 2 firefox (place: query skipped)

    with pytest.raises(crypto.BadPassword):
        backup.plan_restore(host(), path, "nope")
    plan = backup.plan_restore(host(), path, "pw")
    assert {i["id"] for i in plan["items"] if i["compatible"]} == set(ITEMS)

    # Restore on a "new" machine that already has a different VS Code settings file
    # and an installed-but-empty Chrome.
    monkeypatch.setenv("HOME", str(empty_home))
    monkeypatch.setenv("USERPROFILE", str(empty_home))
    (empty_home / ".config/Code/User").mkdir(parents=True)
    (empty_home / ".config/Code/User/settings.json").write_text('{"old": 1}')
    (empty_home / ".config/google-chrome/Default").mkdir(parents=True)
    out = backup.restore(host(), path, "pw", None, lambda s: None, lambda *a: None, CancelToken(), "en")
    assert all(v["ok"] for v in out["items"].values()), out["items"]

    h = empty_home
    assert json.loads((h / ".config/Code/User/settings.json").read_text()) == {"editor.fontSize": 14}
    assert (h / ".config/Code/User/settings.json.keystone-old").read_text() == '{"old": 1}'
    assert (h / ".config/Code/User/snippets/py.json").exists()
    key = h / ".ssh/id_ed25519"
    assert key.read_text() == "PRIVATE"
    if os.name != "nt":
        assert stat.S_IMODE(key.stat().st_mode) == 0o600
        assert stat.S_IMODE((h / ".ssh").stat().st_mode) == 0o700
    assert (h / ".zshrc").exists() and (h / ".config/nvim/init.lua").exists()
    assert (h / ".local/share/fonts/Inter.ttf").exists()
    assert json.loads((h / ".config/google-chrome/Default/Bookmarks").read_text())["roots"]["other"]["children"][0]["name"] == "Flathub"

    html = (h / "Desktop" / "KeyStone-Bookmarks.html").read_text()
    assert html.startswith("<!DOCTYPE NETSCAPE-Bookmark-file-1>")
    assert "Python &lt;docs&gt;" in html and "?a=1&amp;b=2" in html
    assert "Kernel stuff" in html and "place:sort" not in html


def test_unix_items_skipped_on_windows(fake_home, tmp_path):
    path, _, _ = _run_backup(tmp_path)
    plan = backup.plan_restore(host("windows"), path, None)
    compat = {i["id"]: i["compatible"] for i in plan["items"]}
    assert compat["shell"] is False            # bash/zsh files don't belong on Windows
    assert compat["browsers"] and compat["editors"] and compat["git_ssh"] and compat["fonts"]


def test_list_backups(fake_home, tmp_path):
    _run_backup(tmp_path)
    lst = archive.list_backups(tmp_path / "out")
    assert len(lst) == 1 and lst[0]["host"]["os"] == "linux" and not lst[0]["encrypted"]


def test_cancel_stops_backup(fake_home, tmp_path):
    tok = CancelToken()
    tok.cancel()
    from keystone.core.proc import Cancelled
    with pytest.raises(Cancelled):
        backup.backup(host(), ITEMS, tmp_path / "out", None, lambda s: None, lambda *a: None, tok)
    assert not list((tmp_path / "out").glob("*.ksbak")) if (tmp_path / "out").exists() else True
