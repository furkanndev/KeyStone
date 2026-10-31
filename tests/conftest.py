import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from keystone.core.system import SystemInfo  # noqa: E402

BOOKMARKS = {"roots": {
    "bookmark_bar": {"type": "folder", "name": "Bar", "children": [
        {"type": "url", "name": "GitHub", "url": "https://github.com"},
        {"type": "folder", "name": "Docs", "children": [
            {"type": "url", "name": "Python <docs>", "url": "https://docs.python.org/3/?a=1&b=2"}]}]},
    "other": {"type": "folder", "children": [{"type": "url", "name": "Flathub", "url": "https://flathub.org"}]},
    "synced": {"type": "folder", "children": []}}, "version": 1}


def host(os_="linux", distro="ubuntu", like=(), desktop="gnome") -> SystemInfo:
    return SystemInfo(os_, f"{os_} test", "1", "x64", distro_id=distro if os_ == "linux" else "",
                      distro_like=list(like), desktop=desktop, hostname="test-pc", username="u")


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """A populated home directory, set as $HOME."""
    h = tmp_path / "home"

    def w(rel, text, mode=None):
        p = h / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        if mode:
            p.chmod(mode)

    w(".config/google-chrome/Default/Bookmarks", json.dumps(BOOKMARKS))
    w(".config/BraveSoftware/Brave-Browser/Profile 2/Bookmarks", json.dumps(BOOKMARKS))
    ff = h / ".mozilla/firefox/abc.default-release"
    ff.mkdir(parents=True)
    c = sqlite3.connect(ff / "places.sqlite")
    c.executescript("""
      create table moz_places(id integer primary key, url text);
      create table moz_bookmarks(id integer primary key, type int, fk int, parent int, position int, title text, guid text);
      insert into moz_places values (1,'https://mozilla.org'),(2,'https://kernel.org'),(3,'place:sort=8');
      insert into moz_bookmarks values (1,2,null,0,0,'','root________'),(2,2,null,1,0,'menu','menu________'),
        (3,2,null,1,1,'toolbar','toolbar_____'),(10,1,1,3,0,'Mozilla','a'),(11,2,null,3,1,'Kernel stuff','b'),
        (12,1,2,11,0,'Kernel','c'),(13,1,3,2,0,'Recent','d');""")
    c.commit()
    c.close()
    w(".config/Code/User/settings.json", '{"editor.fontSize": 14}')
    w(".config/Code/User/snippets/py.json", "{}")
    w(".gitconfig", "[user]\n name = Test\n")
    w(".ssh/id_ed25519", "PRIVATE", 0o600)
    w(".ssh/id_ed25519.pub", "ssh-ed25519 AAA")
    w(".zshrc", "export X=1\n")
    w(".config/nvim/init.lua", "vim.o.number=true\n")
    w(".local/share/fonts/Inter.ttf", "FONTDATA")
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))       # Windows expanduser()
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    return h


@pytest.fixture
def empty_home(tmp_path):
    h = tmp_path / "home2"
    (h / "Desktop").mkdir(parents=True)
    return h


@pytest.fixture(autouse=True)
def no_external_commands(monkeypatch):
    """Tests must never touch the real system's package managers."""
    from keystone.core import proc
    real = proc.run

    def guarded(cmd, *a, **kw):
        if cmd and os.path.basename(str(cmd[0])) in ("apt-get", "dnf", "pacman", "zypper", "winget", "brew",
                                                     "flatpak", "snap", "sudo", "pkexec", "systemctl", "nmcli",
                                                     "gsettings", "defaults", "dconf"):
            return proc.Result(127, "blocked in tests")
        return real(cmd, *a, **kw)
    monkeypatch.setattr(proc, "run", guarded)
