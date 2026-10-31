"""Saved Wi-Fi networks in a portable format (ssid / security / key).

Windows: netsh XML export (key=clear) / generated XML profile import.
Linux:   NetworkManager via nmcli.
macOS:   preferred networks via networksetup; keys from the login keychain
         (macOS asks for permission per network).
"""
from __future__ import annotations

import json
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

from ...core import proc
from ...core.system import LINUX, MACOS, WINDOWS, which
from ..base import ANY, Ctx, Item

NS = {"w": "http://www.microsoft.com/networking/WLAN/profile/v1"}


def _norm_auth(a: str) -> str:
    a = (a or "").lower()
    if a in ("open", "none", ""):
        return "open"
    if "sae" in a or "wpa3" in a:
        return "sae"
    return "psk"


# ----------------------------------------------------------------------------- windows

def parse_windows_xml(text: str) -> dict | None:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    ssid = root.findtext(".//w:SSIDConfig/w:SSID/w:name", namespaces=NS) or root.findtext("w:name", namespaces=NS)
    if not ssid:
        return None
    return {"ssid": ssid,
            "auth": _norm_auth(root.findtext(".//w:authentication", namespaces=NS) or ""),
            "key": root.findtext(".//w:keyMaterial", namespaces=NS) or "",
            "hidden": (root.findtext(".//w:nonBroadcast", namespaces=NS) or "false") == "true"}


def windows_xml(net: dict) -> str:
    auth = {"open": "open", "psk": "WPA2PSK", "sae": "WPA3SAE"}[net["auth"]]
    enc = "none" if net["auth"] == "open" else "AES"
    sec = "" if net["auth"] == "open" else (
        f"<sharedKey><keyType>passPhrase</keyType><protected>false</protected>"
        f"<keyMaterial>{escape(net['key'])}</keyMaterial></sharedKey>")
    name = escape(net["ssid"])
    return (f'<?xml version="1.0"?><WLANProfile xmlns="{NS["w"]}"><name>{name}</name>'
            f"<SSIDConfig><SSID><name>{name}</name></SSID><nonBroadcast>{str(net.get('hidden', False)).lower()}</nonBroadcast></SSIDConfig>"
            "<connectionType>ESS</connectionType><connectionMode>auto</connectionMode>"
            f"<MSM><security><authEncryption><authentication>{auth}</authentication><encryption>{enc}</encryption>"
            f"<useOneX>false</useOneX></authEncryption>{sec}</security></MSM></WLANProfile>")


def _backup_windows(ctx: Ctx) -> list[dict]:
    raw = ctx.dir / "windows-xml"
    raw.mkdir(parents=True, exist_ok=True)
    proc.run(["netsh", "wlan", "export", "profile", f"folder={raw}", "key=clear"], timeout=60)
    nets = []
    for f in sorted(raw.glob("*.xml")):
        n = parse_windows_xml(f.read_text(encoding="utf-8", errors="replace"))
        if n:
            nets.append(n)
    return nets


def _restore_windows(ctx: Ctx, nets: list[dict]) -> int:
    ok = 0
    with tempfile.TemporaryDirectory() as td:
        for i, n in enumerate(nets):
            f = Path(td) / f"net{i}.xml"
            f.write_text(windows_xml(n), encoding="utf-8")
            if proc.run(["netsh", "wlan", "add", "profile", f"filename={f}", "user=current"], timeout=30).ok:
                ok += 1
                ctx.log(f"Wi-Fi ✓ {n['ssid']}")
    return ok


# ----------------------------------------------------------------------------- linux

def _backup_linux(ctx: Ctx) -> list[dict]:
    if not which("nmcli"):
        return []
    lst = proc.run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"], timeout=30).out
    nets = []
    for line in lst.splitlines():
        name, _, typ = line.rpartition(":")
        if typ != "802-11-wireless":
            continue
        name = name.replace("\\:", ":")
        r = proc.run(["nmcli", "-s", "-t", "-g", "802-11-wireless.ssid,802-11-wireless-security.key-mgmt,"
                      "802-11-wireless-security.psk,802-11-wireless.hidden", "connection", "show", name], timeout=30)
        vals = r.out.splitlines()
        if len(vals) >= 4 and vals[0]:
            km = vals[1].strip()
            nets.append({"ssid": vals[0], "auth": "open" if not km else ("sae" if km == "sae" else "psk"),
                         "key": vals[2], "hidden": vals[3].strip() == "yes"})
    return nets


def _restore_linux(ctx: Ctx, nets: list[dict]) -> int:
    if not which("nmcli"):
        ctx.log("nmcli not found")
        return 0
    existing = set(proc.run(["nmcli", "-t", "-f", "NAME", "connection", "show"], timeout=30).out.splitlines())
    ok = 0
    for n in nets:
        if n["ssid"] in existing:
            continue
        cmd = ["nmcli", "connection", "add", "type", "wifi", "con-name", n["ssid"], "ssid", n["ssid"]]
        if n["auth"] != "open":
            cmd += ["wifi-sec.key-mgmt", "sae" if n["auth"] == "sae" else "wpa-psk", "wifi-sec.psk", n["key"]]
        if n.get("hidden"):
            cmd += ["802-11-wireless.hidden", "yes"]
        if proc.run(cmd, timeout=30).ok:
            ok += 1
            ctx.log(f"Wi-Fi ✓ {n['ssid']}")
    return ok


# ----------------------------------------------------------------------------- macos

def _mac_iface() -> str:
    out = proc.run(["networksetup", "-listallhardwareports"], timeout=15).out.splitlines()
    for i, ln in enumerate(out):
        if ln.strip() in ("Hardware Port: Wi-Fi", "Hardware Port: AirPort") and i + 1 < len(out):
            return out[i + 1].split(":", 1)[1].strip()
    return "en0"


def _backup_macos(ctx: Ctx) -> list[dict]:
    iface = _mac_iface()
    out = proc.run(["networksetup", "-listpreferredwirelessnetworks", iface], timeout=30).out.splitlines()[1:]
    nets = []
    for ssid in (s.strip() for s in out):
        if not ssid:
            continue
        r = proc.run(["security", "find-generic-password", "-D", "AirPort network password", "-a", ssid, "-w"], timeout=90)
        nets.append({"ssid": ssid, "auth": "psk" if r.ok else "open", "key": r.out.strip() if r.ok else "",
                     "hidden": False, "key_missing": not r.ok})
    return nets


def _restore_macos(ctx: Ctx, nets: list[dict]) -> int:
    iface = _mac_iface()
    ok = 0
    for n in nets:
        sec = {"open": "OPEN", "psk": "WPA2", "sae": "WPA3"}.get(n["auth"], "WPA2")
        cmd = ["networksetup", "-addpreferredwirelessnetworkatindex", iface, n["ssid"], "0", sec]
        if n["auth"] != "open":
            cmd.append(n["key"])
        if proc.run(proc.elevate(cmd), env=proc.elevated_env(), timeout=60).ok:
            ok += 1
            ctx.log(f"Wi-Fi ✓ {n['ssid']}")
    return ok


class Wifi(Item):
    id = "wifi"
    name = {"tr": "Wi-Fi ağları", "en": "Wi-Fi networks"}
    desc = {"tr": "Kayıtlı kablosuz ağlar ve parolaları; Windows, macOS ve Linux arasında taşınabilir.",
            "en": "Saved wireless networks and their keys — portable between Windows, macOS and Linux."}
    restore_on = ANY
    sensitive = True

    def detect(self, info):
        if info.os == WINDOWS:
            out = proc.run(["netsh", "wlan", "show", "profiles"], timeout=30).out
            # Localised output; profile lines look like "    <label>   : <ssid>".
            n = sum(1 for ln in out.splitlines() if re.match(r"^\s{2,}\S.*\s:\s*\S", ln))
        elif info.os == LINUX:
            if not which("nmcli"):
                return None
            n = proc.run(["nmcli", "-t", "-f", "TYPE", "connection", "show"], timeout=30).out.count("802-11-wireless")
        else:
            n = max(0, len(proc.run(["networksetup", "-listpreferredwirelessnetworks", _mac_iface()], timeout=30).out.splitlines()) - 1)
        return {"count": n, "size": n * 1024} if n else None

    def backup(self, ctx: Ctx) -> dict:
        fn = {WINDOWS: _backup_windows, LINUX: _backup_linux, MACOS: _backup_macos}[ctx.info.os]
        nets = fn(ctx)
        (ctx.dir / "networks.json").write_text(json.dumps(nets, ensure_ascii=False, indent=1), encoding="utf-8")
        ctx.log(ctx.t(f"{len(nets)} ağ kaydedildi", f"{len(nets)} networks saved"))
        return {"count": len(nets)}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        nets = json.loads((ctx.dir / "networks.json").read_text(encoding="utf-8"))
        fn = {WINDOWS: _restore_windows, LINUX: _restore_linux, MACOS: _restore_macos}[ctx.info.os]
        return {"restored": fn(ctx, [n for n in nets if n["auth"] == "open" or n.get("key")])}
