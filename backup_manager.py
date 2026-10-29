"""
RetroFormat Backup & Restore Manager
Safely backs up application configurations and system settings before formatting,
and restores them seamlessly on a fresh Windows installation.
"""

import os
import sys
import shutil
import json
import subprocess
import winreg
import html
import sqlite3
from datetime import datetime
import xml.etree.ElementTree as ET


def get_no_window_kwargs() -> dict:
    """Returns subprocess kwargs to completely suppress any console window on Windows."""
    kwargs = {}
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def get_user_dir():
    return os.environ.get("USERPROFILE", os.path.expanduser("~"))


def get_appdata():
    return os.environ.get("APPDATA", os.path.join(get_user_dir(), "AppData", "Roaming"))


def get_localappdata():
    return os.environ.get("LOCALAPPDATA", os.path.join(get_user_dir(), "AppData", "Local"))


# =============================================================================
# BACKUP & RESTORE IMPLEMENTATIONS
# =============================================================================

def backup_vscode(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Backup VS Code user settings, keybindings, snippets and extension list."""
    try:
        dest = os.path.join(target_dir, "vscode")
        os.makedirs(dest, exist_ok=True)
        src_user = os.path.join(get_appdata(), "Code", "User")

        copied_files = 0
        if os.path.exists(src_user):
            for filename in ["settings.json", "keybindings.json"]:
                file_path = os.path.join(src_user, filename)
                if os.path.exists(file_path):
                    shutil.copy2(file_path, os.path.join(dest, filename))
                    copied_files += 1

            snippets_dir = os.path.join(src_user, "snippets")
            if os.path.exists(snippets_dir):
                dest_snippets = os.path.join(dest, "snippets")
                if os.path.exists(dest_snippets):
                    shutil.rmtree(dest_snippets)
                shutil.copytree(snippets_dir, dest_snippets)

        # Export extensions list
        ext_file = os.path.join(dest, "extensions.txt")
        try:
            res = subprocess.run(["code", "--list-extensions"], capture_output=True, text=True, shell=True, **get_no_window_kwargs())
            if res.returncode == 0 and res.stdout.strip():
                with open(ext_file, "w", encoding="utf-8") as f:
                    f.write(res.stdout.strip())
                if log_fn:
                    log_fn(f"[YEDEK] VS Code: {len(res.stdout.strip().splitlines())} adet eklenti listesi kaydedildi.")
        except Exception:
            pass

        if log_fn:
            log_fn(f"[YEDEK] VS Code ayarları ve eklentileri '{dest}' konumuna yedeklendi.")
        return True, "VS Code ayarları ve eklentileri başarıyla yedeklendi."
    except Exception as e:
        return False, f"VS Code yedekleme hatası: {e}"


def restore_vscode(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Restore VS Code configuration and re-install backed up extensions."""
    try:
        src = os.path.join(backup_dir, "vscode")
        if not os.path.exists(src):
            return False, "Yedek klasöründe VS Code verisi bulunamadı."

        dest_user = os.path.join(get_appdata(), "Code", "User")
        os.makedirs(dest_user, exist_ok=True)

        for filename in ["settings.json", "keybindings.json"]:
            file_path = os.path.join(src, filename)
            if os.path.exists(file_path):
                shutil.copy2(file_path, os.path.join(dest_user, filename))

        src_snippets = os.path.join(src, "snippets")
        if os.path.exists(src_snippets):
            dest_snippets = os.path.join(dest_user, "snippets")
            if os.path.exists(dest_snippets):
                shutil.rmtree(dest_snippets)
            shutil.copytree(src_snippets, dest_snippets)

        ext_file = os.path.join(src, "extensions.txt")
        if os.path.exists(ext_file):
            with open(ext_file, "r", encoding="utf-8") as f:
                extensions = [line.strip() for line in f if line.strip()]
            if log_fn:
                log_fn(f"[GERİ YÜKLE] {len(extensions)} adet VS Code eklentisi kuruluyor...")

            code_bin = "code"
            if not shutil.which("code"):
                candidates = [
                    os.path.join(get_localappdata(), "Programs", "Microsoft VS Code", "bin", "code.cmd"),
                    r"C:\Program Files\Microsoft VS Code\bin\code.cmd"
                ]
                for c in candidates:
                    if os.path.exists(c):
                        code_bin = c
                        break

            for ext in extensions:
                subprocess.run([code_bin, "--install-extension", ext], capture_output=True, shell=True, **get_no_window_kwargs())

        if log_fn:
            log_fn("[GERİ YÜKLE] VS Code ayarları ve eklentileri sisteme yüklendi.")
        return True, "VS Code ayarları geri yüklendi."
    except Exception as e:
        return False, f"VS Code geri yükleme hatası: {e}"


def backup_git_ssh(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Backup .gitconfig and SSH credentials."""
    try:
        dest = os.path.join(target_dir, "git_ssh")
        os.makedirs(dest, exist_ok=True)
        user_dir = get_user_dir()

        gitconfig = os.path.join(user_dir, ".gitconfig")
        if os.path.exists(gitconfig):
            shutil.copy2(gitconfig, os.path.join(dest, ".gitconfig"))

        ssh_dir = os.path.join(user_dir, ".ssh")
        if os.path.exists(ssh_dir):
            dest_ssh = os.path.join(dest, ".ssh")
            if os.path.exists(dest_ssh):
                shutil.rmtree(dest_ssh)
            shutil.copytree(ssh_dir, dest_ssh)

        if log_fn:
            log_fn(f"[YEDEK] Git yapılandırması ve SSH anahtarları '{dest}' klasörüne kaydedildi.")
        return True, "Git ve SSH verileri yedeklendi."
    except Exception as e:
        return False, f"Git/SSH yedekleme hatası: {e}"


def restore_git_ssh(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Restore .gitconfig and SSH keys."""
    try:
        src = os.path.join(backup_dir, "git_ssh")
        if not os.path.exists(src):
            return False, "Yedek klasöründe Git/SSH verisi bulunamadı."

        user_dir = get_user_dir()
        gitconfig = os.path.join(src, ".gitconfig")
        if os.path.exists(gitconfig):
            shutil.copy2(gitconfig, os.path.join(user_dir, ".gitconfig"))

        src_ssh = os.path.join(src, ".ssh")
        if os.path.exists(src_ssh):
            dest_ssh = os.path.join(user_dir, ".ssh")
            os.makedirs(dest_ssh, exist_ok=True)
            for item in os.listdir(src_ssh):
                s = os.path.join(src_ssh, item)
                d = os.path.join(dest_ssh, item)
                if os.path.isfile(s):
                    shutil.copy2(s, d)

        if log_fn:
            log_fn("[GERİ YÜKLE] Git profili ve SSH anahtarları kullanıcı dizinine aktarıldı.")
        return True, "Git ve SSH verileri geri yüklendi."
    except Exception as e:
        return False, f"Git/SSH geri yükleme hatası: {e}"


def backup_wifi(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Export all saved Wi-Fi networks with passwords in clear text, plus human-readable TXT and 1-click BAT."""
    try:
        dest = os.path.join(target_dir, "wifi")
        os.makedirs(dest, exist_ok=True)
        abs_dest = os.path.abspath(dest)

        cmd = f'netsh wlan export profile folder="{abs_dest}" key=clear'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, **get_no_window_kwargs())

        xml_files = [f for f in os.listdir(dest) if f.endswith(".xml")]

        txt_lines = [
            "=" * 60,
            "KEYSTONE - KAYITLI WI-FI AGLARI VE SIFRELERI",
            f"Yedekleme Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "=" * 60,
            ""
        ]

        bat_lines = [
            "@echo off",
            "chcp 65001 >nul",
            "echo ====================================================",
            "echo WI-FI AGLARI SISTEME GERI YUKLENIYOR...",
            "echo ====================================================",
            "echo.",
            'cd /d "%~dp0"'
        ]

        parsed_count = 0
        for f in xml_files:
            xml_full = os.path.join(dest, f)
            bat_lines.append(f'netsh wlan add profile filename="%~dp0{f}" user=all')
            try:
                tree = ET.parse(xml_full)
                root = tree.getroot()
                ns = {'w': 'http://www.microsoft.com/networking/WLAN/profile/v1'}
                name = root.find('w:name', ns)
                name_str = name.text if name is not None else f
                key_mat = root.find('.//w:keyMaterial', ns)
                pwd = key_mat.text if key_mat is not None else '(Sifresiz / Acik Ag)'
                auth = root.find('.//w:authentication', ns)
                auth_str = auth.text if auth is not None else 'WPA2/WPA3'

                parsed_count += 1
                txt_lines.append(f"{parsed_count}. Ag Adi (SSID) : {name_str}")
                txt_lines.append(f"   Sifre         : {pwd}")
                txt_lines.append(f"   Guvenlik      : {auth_str}")
                txt_lines.append("-" * 40)
            except Exception:
                pass

        bat_lines.append("echo.")
        bat_lines.append("echo [BASARILI] Tum Wi-Fi aglari basariyla eklendi!")
        bat_lines.append("pause")

        txt_content = "\n".join(txt_lines)
        with open(os.path.join(dest, "wifi_sifreleri.txt"), "w", encoding="utf-8") as f_txt:
            f_txt.write(txt_content)
        # Also write in root target_dir for instant convenience
        with open(os.path.join(target_dir, "wifi_sifreleri.txt"), "w", encoding="utf-8") as f_txt:
            f_txt.write(txt_content)

        with open(os.path.join(dest, "tum_wifileri_yukle.bat"), "w", encoding="utf-8") as f_bat:
            f_bat.write("\n".join(bat_lines))

        if log_fn:
            log_fn(f"[YEDEK] {len(xml_files)} adet Wi-Fi profili 'wifi/' klasörüne aktarıldı.")
            log_fn(f"[YEDEK] Şifreleri doğrudan okumak için 'wifi_sifreleri.txt' oluşturuldu.")
            log_fn(f"[İPUCU] Format sonrası doğrudan 'tum_wifileri_yukle.bat' çalıştırarak veya uygulamadan 'Geri Yükle' diyerek yükleyebilirsiniz.")

        return True, f"{len(xml_files)} adet Wi-Fi ağı şifreleriyle birlikte yedeklendi."
    except Exception as e:
        return False, f"Wi-Fi yedekleme hatası: {e}"


def restore_wifi(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Import and register saved Wi-Fi network profiles."""
    try:
        src = os.path.join(backup_dir, "wifi")
        if not os.path.exists(src):
            return False, "Yedek klasöründe Wi-Fi profili bulunamadı."

        xml_files = [os.path.join(src, f) for f in os.listdir(src) if f.endswith(".xml")]
        count = 0
        for xml in xml_files:
            abs_xml = os.path.abspath(xml)
            cmd = f'netsh wlan add profile filename="{abs_xml}" user=all'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, **get_no_window_kwargs())
            if res.returncode == 0:
                count += 1
                fname = os.path.basename(xml)
                if log_fn:
                    log_fn(f"[GERİ YÜKLE] Wi-Fi ağı sisteme eklendi: {fname}")

        if log_fn:
            log_fn(f"[GERİ YÜKLE] Toplam {count} adet Wi-Fi ağı sisteme başarıyla kaydedildi. Windows otomatik bağlanacaktır.")
        return True, f"{count} adet Wi-Fi profili geri yüklendi."
    except Exception as e:
        return False, f"Wi-Fi geri yükleme hatası: {e}"


def _safe_copy_file(src: str, dst: str):
    """Safely copies a file even if locked for writing by a browser."""
    try:
        shutil.copy2(src, dst)
    except Exception:
        with open(src, "rb") as f_in:
            with open(dst, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)


def chromium_json_to_netscape_html_section(roots_dict: dict, label: str = "Tarayıcı") -> str:
    """Generate Netscape HTML bookmark section from Chromium roots JSON."""
    lines = [
        f"    <DT><H3>{html.escape(label)}</H3>",
        "    <DL><p>"
    ]

    def process_node(node, indent=2):
        ind = "    " * indent
        ntype = node.get("type")
        name = html.escape(node.get("name", "İsimsiz"))

        if ntype == "url":
            url = html.escape(node.get("url", ""))
            date_added = node.get("date_added", "0")
            lines.append(f'{ind}<DT><A HREF="{url}" ADD_DATE="{date_added}">{name}</A>')
        elif ntype == "folder":
            date_added = node.get("date_added", "0")
            date_modified = node.get("date_modified", "0")
            lines.append(f'{ind}<DT><H3 ADD_DATE="{date_added}" LAST_MODIFIED="{date_modified}">{name}</H3>')
            lines.append(f"{ind}<DL><p>")
            for child in node.get("children", []):
                process_node(child, indent + 1)
            lines.append(f"{ind}</DL><p>")

    label_map = {
        "bookmark_bar": "Yer İmleri Çubuğu",
        "other": "Diğer Yer İmleri",
        "synced": "Mobil & Senkronize"
    }

    has_content = False
    for root_key, sub_label in label_map.items():
        root_node = roots_dict.get(root_key)
        if root_node and root_node.get("children"):
            has_content = True
            lines.append(f"        <DT><H3>{sub_label}</H3>")
            lines.append("        <DL><p>")
            for child in root_node.get("children", []):
                process_node(child, 3)
            lines.append("        </DL><p>")

    lines.append("    </DL><p>")
    return "\n".join(lines) if has_content else ""


def extract_firefox_bookmarks_to_html(places_path: str, profile_name: str = "Firefox") -> str:
    """Extract bookmarks from Firefox places.sqlite and return Netscape HTML section."""
    try:
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_db = os.path.join(temp_dir, f"ff_temp_{os.path.basename(places_path)}")
        shutil.copy2(places_path, temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.title, p.url, b.dateAdded
            FROM moz_bookmarks b
            JOIN moz_places p ON b.fk = p.id
            WHERE b.type = 1 AND p.url IS NOT NULL
            ORDER BY b.dateAdded ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        try:
            os.remove(temp_db)
        except Exception:
            pass

        if not rows:
            return ""

        lines = [
            f"    <DT><H3>{html.escape(profile_name)} Yer İmleri</H3>",
            "    <DL><p>"
        ]
        for title, url, date_added in rows:
            if not title:
                title = url
            lines.append(f'        <DT><A HREF="{html.escape(url)}" ADD_DATE="{date_added or 0}">{html.escape(title)}</A>')
        lines.append("    </DL><p>")
        return "\n".join(lines)
    except Exception:
        return ""


def wrap_netscape_html(title: str, body_sections: list[str]) -> str:
    """Wrap bookmark sections in standard Netscape Bookmark HTML format."""
    header = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file. DO NOT EDIT! -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        f"<TITLE>{html.escape(title)}</TITLE>",
        f"<H1>{html.escape(title)}</H1>",
        "<DL><p>"
    ]
    footer = [
        "</DL><p>"
    ]
    return "\n".join(header + body_sections + footer)


def clean_firefox_profile_name(p: str) -> str:
    """Extract a clean, human-readable profile name from Firefox profile folder."""
    if "." in p:
        parts = p.split(".", 1)
        name = parts[1]
        if "default-release" in name:
            return "default-release"
        return name
    return p


def has_chromium_bookmarks(bm_path: str) -> bool:
    """Check if Chromium bookmarks file has at least one saved bookmark."""
    try:
        with open(bm_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        roots = data.get("roots", {})
        for k in ["bookmark_bar", "other", "synced"]:
            node = roots.get(k)
            if node and node.get("children"):
                return True
        return False
    except Exception:
        return False


def count_firefox_bookmarks(places_path: str) -> int:
    """Count user bookmarks stored in Firefox places.sqlite."""
    try:
        import tempfile
        t = os.path.join(tempfile.gettempdir(), f"ff_cnt_{os.path.basename(places_path)}")
        shutil.copy2(places_path, t)
        conn = sqlite3.connect(t)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM moz_bookmarks WHERE type = 1")
        cnt = cursor.fetchone()[0]
        conn.close()
        try:
            os.remove(t)
        except Exception:
            pass
        return cnt
    except Exception:
        return 0


def backup_browsers(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Backup Chrome, Brave, Edge, Opera, Opera GX, Vivaldi, Thorium, and Firefox bookmarks as timestamped HTML files in dedicated folders."""
    try:
        dest = os.path.join(target_dir, "browsers")
        os.makedirs(dest, exist_ok=True)
        local_app = get_localappdata()
        app_data = get_appdata()
        saved = []
        manifest = {}
        all_html_sections = []

        # Current timestamp formatted as DD.MM.YYYY_HH.MM
        ts = datetime.now().strftime("%d.%m.%Y_%H.%M")

        # 1. Chromium based browsers
        chromium_browsers = [
            ("Brave", os.path.join(local_app, "BraveSoftware", "Brave-Browser", "User Data")),
            ("Chrome", os.path.join(local_app, "Google", "Chrome", "User Data")),
            ("Edge", os.path.join(local_app, "Microsoft", "Edge", "User Data")),
            ("Opera", os.path.join(app_data, "Opera Software", "Opera Stable")),
            ("OperaGX", os.path.join(app_data, "Opera Software", "Opera GX Stable")),
            ("Vivaldi", os.path.join(local_app, "Vivaldi", "User Data")),
            ("Thorium", os.path.join(local_app, "Thorium", "User Data")),
            ("Helium", os.path.join(local_app, "Helium", "User Data")),
            ("Helium", os.path.join(local_app, "ImputNet", "Helium", "User Data")),
        ]

        for b_name, base_path in chromium_browsers:
            if not os.path.exists(base_path):
                continue

            profiles = []
            # Direct Bookmarks (Opera, portable Chromium)
            direct_bm = os.path.join(base_path, "Bookmarks")
            if os.path.exists(direct_bm) and has_chromium_bookmarks(direct_bm):
                profiles.append(("Default", direct_bm))

            # Profile subfolders inside User Data (Default, Profile 1, Profile 2...)
            try:
                for entry in os.listdir(base_path):
                    if entry in ["Guest Profile", "System Profile"]:
                        continue
                    entry_path = os.path.join(base_path, entry)
                    if os.path.isdir(entry_path):
                        bm_path = os.path.join(entry_path, "Bookmarks")
                        if os.path.exists(bm_path) and has_chromium_bookmarks(bm_path):
                            if not any(p[1] == bm_path for p in profiles):
                                profiles.append((entry, bm_path))
            except Exception:
                pass

            if not profiles:
                continue

            # Dedicated folder per browser
            browser_dir = os.path.join(dest, b_name)
            os.makedirs(browser_dir, exist_ok=True)
            browser_sections = []
            is_single = len(profiles) == 1

            for prof_name, bm_path in profiles:
                clean_name = prof_name.replace(" ", "_")
                if is_single:
                    target_folder = browser_dir
                    html_name = f"{b_name}_Yer_Imleri_{ts}.html"
                    label = f"{b_name}"
                else:
                    target_folder = os.path.join(browser_dir, clean_name)
                    os.makedirs(target_folder, exist_ok=True)
                    html_name = f"{b_name}_{clean_name}_Yer_Imleri_{ts}.html"
                    label = f"{b_name} ({prof_name})"

                html_out = os.path.join(target_folder, html_name)

                try:
                    # Read Chromium JSON to generate HTML and keep in manifest for 1-click restore
                    with open(bm_path, "r", encoding="utf-8") as f_bm:
                        bm_json = json.load(f_bm)

                    manifest[f"{b_name}/{clean_name}"] = {
                        "type": "chromium",
                        "target": bm_path,
                        "data": bm_json
                    }
                    saved.append(label)

                    sec = chromium_json_to_netscape_html_section(bm_json.get("roots", {}), label)
                    if sec:
                        all_html_sections.append(sec)
                        browser_sections.append(sec)
                        single_html = wrap_netscape_html(f"{label} Yer İmleri ({ts})", [sec])
                        with open(html_out, "w", encoding="utf-8") as f_h:
                            f_h.write(single_html)
                        # Also write bookmarks.html for default 1-click browser import
                        with open(os.path.join(target_folder, "bookmarks.html"), "w", encoding="utf-8") as f_h:
                            f_h.write(single_html)

                    if log_fn:
                        log_fn(f"[YEDEK] {label} -> 'browsers/{b_name}/' klasörüne '{html_name}' olarak kaydedildi.")
                except Exception as e:
                    if log_fn:
                        log_fn(f"[UYARI] {label} yer imi dönüştürülürken hata: {e}")

            # If browser has multiple profiles, provide combined HTML in browser root
            if not is_single and browser_sections:
                combined_b_html = wrap_netscape_html(f"{b_name} Tüm Yer İmleri ({ts})", browser_sections)
                with open(os.path.join(browser_dir, f"{b_name}_Tum_Yer_Imleri_{ts}.html"), "w", encoding="utf-8") as f_h:
                    f_h.write(combined_b_html)
                with open(os.path.join(browser_dir, "bookmarks.html"), "w", encoding="utf-8") as f_h:
                    f_h.write(combined_b_html)

        # 2. Firefox
        ff_profiles_dir = os.path.join(app_data, "Mozilla", "Firefox", "Profiles")
        if os.path.exists(ff_profiles_dir):
            ff_profiles = []
            try:
                for p in os.listdir(ff_profiles_dir):
                    p_dir = os.path.join(ff_profiles_dir, p)
                    if os.path.isdir(p_dir):
                        places_db = os.path.join(p_dir, "places.sqlite")
                        if os.path.exists(places_db):
                            cnt = count_firefox_bookmarks(places_db)
                            if cnt > 0:
                                ff_profiles.append((p, places_db, cnt))
            except Exception:
                pass

            if ff_profiles:
                browser_dir = os.path.join(dest, "Firefox")
                os.makedirs(browser_dir, exist_ok=True)
                browser_sections = []
                is_single = len(ff_profiles) == 1

                for p, places_db, cnt in ff_profiles:
                    display_name = clean_firefox_profile_name(p)
                    if is_single:
                        target_folder = browser_dir
                        html_name = f"Firefox_Yer_Imleri_{ts}.html"
                        label = "Firefox"
                    else:
                        target_folder = os.path.join(browser_dir, display_name)
                        os.makedirs(target_folder, exist_ok=True)
                        html_name = f"Firefox_{display_name}_Yer_Imleri_{ts}.html"
                        label = f"Firefox ({display_name})"

                    html_out = os.path.join(target_folder, html_name)

                    try:
                        sec = extract_firefox_bookmarks_to_html(places_db, label)
                        if sec:
                            all_html_sections.append(sec)
                            browser_sections.append(sec)
                            single_html = wrap_netscape_html(f"{label} Yer İmleri ({ts})", [sec])
                            with open(html_out, "w", encoding="utf-8") as f_h:
                                f_h.write(single_html)
                            with open(os.path.join(target_folder, "bookmarks.html"), "w", encoding="utf-8") as f_h:
                                f_h.write(single_html)

                        saved.append(label)
                        manifest[f"Firefox/{display_name}"] = {
                            "type": "firefox_html",
                            "target": places_db,
                            "html_file": html_name
                        }
                        if log_fn:
                            log_fn(f"[YEDEK] {label} ({cnt} yer imi) -> 'browsers/Firefox/' klasörüne '{html_name}' olarak kaydedildi.")
                    except Exception as e:
                        if log_fn:
                            log_fn(f"[UYARI] {label} yer imi dönüştürülürken hata: {e}")

                if not is_single and browser_sections:
                    combined_b_html = wrap_netscape_html(f"Firefox Tüm Yer İmleri ({ts})", browser_sections)
                    with open(os.path.join(browser_dir, f"Firefox_Tum_Yer_Imleri_{ts}.html"), "w", encoding="utf-8") as f_h:
                        f_h.write(combined_b_html)
                    with open(os.path.join(browser_dir, "bookmarks.html"), "w", encoding="utf-8") as f_h:
                        f_h.write(combined_b_html)

        # Save manifest mapping for 100% accurate native restore
        manifest_file = os.path.join(dest, "manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Generate combined bookmarks.html in root target_dir and inside browsers/
        if all_html_sections:
            combined_html = wrap_netscape_html(f"Keystone - Tüm Tarayıcı Yer İmleri ({ts})", all_html_sections)
            # 1. Main root bookmarks.html with timestamp & standard name
            root_bm_html = os.path.join(target_dir, f"bookmarks_{ts}.html")
            with open(root_bm_html, "w", encoding="utf-8") as f:
                f.write(combined_html)
            with open(os.path.join(target_dir, "bookmarks.html"), "w", encoding="utf-8") as f:
                f.write(combined_html)
            # 2. Inside browsers/ folder as well
            with open(os.path.join(dest, f"tum_tarayici_yer_imleri_{ts}.html"), "w", encoding="utf-8") as f:
                f.write(combined_html)
            with open(os.path.join(dest, "tum_tarayici_yer_imleri.html"), "w", encoding="utf-8") as f:
                f.write(combined_html)
            with open(os.path.join(dest, "bookmarks.html"), "w", encoding="utf-8") as f:
                f.write(combined_html)

            if log_fn:
                log_fn(f"[HTML YEDEK] Tüm yer imleri tarih-saatli ({ts}) HTML olarak klasörlere ayrıldı.")
                log_fn("[BİLGİ] HTML dosyalarını Chrome, Edge, Brave, Opera veya Firefox'ta 'Yer İmlerini İçe Aktar' ile doğrudan yükleyebilirsiniz.")

        if not saved:
            return True, "Sistemde yer imi tespit edilemedi veya tarayıcılar henüz kullanılmadı."

        return True, f"Tarayıcı yer imleri ({len(saved)} profil) tarih-saatli HTML olarak klasörlendi."
    except Exception as e:
        return False, f"Tarayıcı yedekleme hatası: {e}"


def restore_browsers(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Restore browser bookmarks to respective profiles."""
    try:
        src = os.path.join(backup_dir, "browsers")
        if not os.path.exists(src):
            return False, "Yedek klasöründe tarayıcı verisi bulunamadı."

        manifest_file = os.path.join(src, "manifest.json")
        restored_count = 0

        # Method 1: Restore using manifest mapping
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)

                for item_key, item_info in manifest.items():
                    if isinstance(item_info, dict):
                        itype = item_info.get("type")
                        target = item_info.get("target")
                        if itype == "chromium" and "data" in item_info and target:
                            os.makedirs(os.path.dirname(target), exist_ok=True)
                            with open(target, "w", encoding="utf-8") as f_out:
                                json.dump(item_info["data"], f_out, indent=2)
                            restored_count += 1
                            if log_fn:
                                log_fn(f"[GERİ YÜKLE] Chromium yer imleri geri yüklendi: {target}")
                        elif itype == "firefox_html" and log_fn:
                            log_fn(f"[GERİ YÜKLE - BİLGİ] Firefox yer imlerini yüklemek için: Firefox -> Yer İmleri (Ctrl+Shift+O) -> 'Yer İmlerini İçe Aktar' menüsünden yedeklenen HTML dosyasını seçebilirsiniz.")
                    elif isinstance(item_info, str):
                        # Legacy mapping where key is out_name, value is target_path
                        target_path = item_info
                        src_file = os.path.join(src, item_key)
                        if not os.path.exists(src_file):
                            base = os.path.basename(item_key)
                            for root, _, files in os.walk(src):
                                if base in files:
                                    src_file = os.path.join(root, base)
                                    break
                        if os.path.exists(src_file):
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            _safe_copy_file(src_file, target_path)
                            restored_count += 1
                            if log_fn:
                                log_fn(f"[GERİ YÜKLE] Yer imleri '{target_path}' konumuna aktarıldı.")
            except Exception as e:
                if log_fn:
                    log_fn(f"[UYARI] Manifest ile geri yükleme hatası: {e}")

        # Method 2: Fallback for HTML or JSON files if manifest wasn't enough
        if restored_count == 0:
            local_app = get_localappdata()
            std_targets = [
                (os.path.join("Brave", "Bookmarks.json"), os.path.join(local_app, "BraveSoftware", "Brave-Browser", "User Data", "Default", "Bookmarks")),
                (os.path.join("Chrome", "Bookmarks.json"), os.path.join(local_app, "Google", "Chrome", "User Data", "Default", "Bookmarks")),
                (os.path.join("Edge", "Bookmarks.json"), os.path.join(local_app, "Microsoft", "Edge", "User Data", "Default", "Bookmarks")),
            ]
            for fname, target in std_targets:
                s = os.path.join(src, fname)
                if not os.path.exists(s):
                    base = os.path.basename(fname)
                    for root, _, files in os.walk(src):
                        if base in files:
                            s = os.path.join(root, base)
                            break
                if os.path.exists(s):
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    _safe_copy_file(s, target)
                    restored_count += 1
                    if log_fn:
                        log_fn(f"[GERİ YÜKLE] Profil yüklendi: {target}")

        if log_fn:
            log_fn("[İPUCU] Tüm tarayıcılarda (Chrome, Brave, Edge, Firefox, Opera) Menü -> Yer İmleri -> 'Yer İmlerini İçe Aktar (HTML)' seçeneğiyle tarih-saatli HTML dosyanızı tek tıkla yükleyebilirsiniz.")

        return True, f"{restored_count} adet tarayıcı yer imi profili geri yüklendi."
    except Exception as e:
        return False, f"Tarayıcı geri yükleme hatası: {e}"


def backup_env_vars(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Backup user environment variables from HKCU\\Environment."""
    try:
        dest = os.path.join(target_dir, "environment")
        os.makedirs(dest, exist_ok=True)

        env_dict = {}
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ)
        idx = 0
        while True:
            try:
                name, val, typ = winreg.EnumValue(key, idx)
                env_dict[name] = {"value": val, "type": typ}
                idx += 1
            except OSError:
                break
        winreg.CloseKey(key)

        out_file = os.path.join(dest, "user_env.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(env_dict, f, indent=2)

        if log_fn:
            log_fn(f"[YEDEK] {len(env_dict)} adet kullanıcı ortam değişkeni (PATH dahil) kaydedildi.")
        return True, "Ortam değişkenleri yedeklendi."
    except Exception as e:
        return False, f"Ortam değişkenleri yedekleme hatası: {e}"


def restore_env_vars(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Restore user environment variables into HKCU\\Environment."""
    try:
        file_path = os.path.join(backup_dir, "environment", "user_env.json")
        if not os.path.exists(file_path):
            return False, "Yedek klasöründe ortam değişkenleri bulunamadı."

        with open(file_path, "r", encoding="utf-8") as f:
            env_dict = json.load(f)

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Environment")
        count = 0
        for name, info in env_dict.items():
            winreg.SetValueEx(key, name, 0, info.get("type", winreg.REG_SZ), info.get("value", ""))
            count += 1
        winreg.CloseKey(key)

        if log_fn:
            log_fn(f"[GERİ YÜKLE] {count} adet ortam değişkeni kayıt defterine yazıldı.")
        return True, "Ortam değişkenleri geri yüklendi."
    except Exception as e:
        return False, f"Ortam değişkenleri geri yükleme hatası: {e}"


def get_installed_windows_apps() -> list[dict]:
    """Scan Windows Registry for installed software across 32-bit and 64-bit hives."""
    apps = []
    seen = set()
    targets = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for root, subkey in targets:
        try:
            with winreg.OpenKey(root, subkey) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    try:
                        sk_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sk_name) as app_key:
                            def get_val(name):
                                try:
                                    v, _ = winreg.QueryValueEx(app_key, name)
                                    return str(v).strip()
                                except Exception:
                                    return ""

                            if get_val("SystemComponent") == "1" or get_val("ParentKeyName"):
                                continue
                            if get_val("ReleaseType").lower() == "security update":
                                continue

                            name = get_val("DisplayName")
                            if not name:
                                continue

                            version = get_val("DisplayVersion")
                            publisher = get_val("Publisher")
                            install_date = get_val("InstallDate")

                            dedup = f"{name.lower()}|{version.lower()}"
                            if dedup in seen:
                                continue
                            seen.add(dedup)

                            apps.append({
                                "name": name,
                                "version": version,
                                "publisher": publisher,
                                "install_date": install_date
                            })
                    except Exception:
                        pass
        except Exception:
            pass

    apps.sort(key=lambda x: x["name"].lower())
    return apps


def backup_installed_apps(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Backup list of all installed software from Registry and export Winget manifest."""
    try:
        dest = os.path.join(target_dir, "installed_apps")
        os.makedirs(dest, exist_ok=True)
        ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        apps = get_installed_windows_apps()

        # Check matching Keystone packages
        matched_keystone = []
        try:
            from data.packages import PACKAGES
            app_names_lower = {a["name"].lower() for a in apps}
            for pkg in PACKAGES:
                p_name = pkg["name"].lower()
                if any(p_name in an for an in app_names_lower) or pkg.get("winget_id", "").lower() in app_names_lower:
                    matched_keystone.append(pkg)
        except Exception:
            pass

        # 1. Text report
        report_lines = [
            "=" * 78,
            "KEYSTONE - KURULU PROGRAMLAR YEDEK RAPORU",
            f"Tarih: {ts}",
            f"Toplam Tespit Edilen Sistem Uygulamasi: {len(apps)}",
            "=" * 78,
            ""
        ]

        if matched_keystone:
            report_lines.append("[+] KEYSTONE KATALOĞUNDAN TESPİT EDİLEN PROGRAMLAR:")
            for kp in matched_keystone:
                report_lines.append(f"  • {kp['name']} [{kp['id']}] - Kategori: {kp.get('category', 'diger')}")
            report_lines.append("")

        report_lines.append("[+] SİSTEMDE KURULU TÜM YAZILIMLAR:")
        for a in apps:
            pub = f" ({a['publisher']})" if a["publisher"] else ""
            ver = f" - v{a['version']}" if a["version"] else ""
            report_lines.append(f"  • {a['name']}{ver}{pub}")

        report_text = "\n".join(report_lines)
        report_file = os.path.join(dest, "kurulu_programlar.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        with open(os.path.join(target_dir, "kurulu_programlar.txt"), "w", encoding="utf-8") as f:
            f.write(report_text)

        # 2. JSON data
        json_data = {
            "export_time": ts,
            "total_count": len(apps),
            "matched_keystone_package_ids": [kp["id"] for kp in matched_keystone],
            "installed_programs": apps
        }
        json_file = os.path.join(dest, "installed_programs.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # 3. Winget export if available
        winget_exported = False
        if shutil.which("winget") is not None:
            winget_file = os.path.join(dest, "winget_packages.json")
            cmd = f'winget export -o "{winget_file}" --accept-source-agreements'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, **get_no_window_kwargs())
            if os.path.exists(winget_file):
                winget_exported = True
                shutil.copy2(winget_file, os.path.join(target_dir, "winget_packages.json"))
                if log_fn:
                    log_fn(f"[YEDEK] Winget paket manifestosu 'winget_packages.json' olarak kaydedildi.")

        if log_fn:
            log_fn(f"[YEDEK] {len(apps)} adet kurulu uygulama listelendi ve 'kurulu_programlar.txt' olarak kaydedildi.")

        msg = f"{len(apps)} adet kurulu program listelendi ve yedeklendi."
        if winget_exported:
            msg += " (Winget manifestosu dahil)"
        return True, msg
    except Exception as e:
        return False, f"Kurulu programları yedekleme hatası: {e}"


def restore_installed_apps(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Import and auto-install supported packages via Winget, and display previous app list."""
    try:
        winget_file = os.path.join(backup_dir, "winget_packages.json")
        if not os.path.exists(winget_file):
            winget_file = os.path.join(backup_dir, "installed_apps", "winget_packages.json")

        winget_installed = False
        if os.path.exists(winget_file) and shutil.which("winget") is not None:
            if log_fn:
                log_fn("[GERİ YÜKLE] Winget import komutu başlatılıyor (Arka planda kurulacak)...")
            cmd = f'winget import -i "{winget_file}" --accept-package-agreements --accept-source-agreements --ignore-unavailable'
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **get_no_window_kwargs())
            if log_fn and proc.stdout:
                for line in iter(proc.stdout.readline, ''):
                    if line.strip():
                        log_fn(f"[WINGET] {line.strip()}")
                proc.stdout.close()
            proc.wait()
            winget_installed = True

        report_file = os.path.join(backup_dir, "kurulu_programlar.txt")
        if not os.path.exists(report_file):
            report_file = os.path.join(backup_dir, "installed_apps", "kurulu_programlar.txt")

        if os.path.exists(report_file) and log_fn:
            log_fn(f"[BİLGİ] Format öncesinde kurulu programların listesi '{report_file}' konumunda hazır bulunmaktadır.")

        if winget_installed:
            return True, "Winget üzerinden desteklenen tüm programlar otomatik olarak kuruldu."
        elif os.path.exists(report_file):
            return True, "Kurulu programlar listesi incelendi (Otomatik Winget yedeği bulunamadı)."
        return False, "Yedek klasöründe kurulu program verisi bulunamadı."
    except Exception as e:
        return False, f"Kurulu programları geri yükleme hatası: {e}"


def backup_winget_manifest(target_dir: str, log_fn=None) -> tuple[bool, str]:
    return backup_installed_apps(target_dir, log_fn=log_fn)


def restore_winget_manifest(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    return restore_installed_apps(backup_dir, log_fn=log_fn)


def backup_active_tweaks(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Backup active Windows registry tweaks as .reg file and JSON manifest."""
    try:
        from data.tweaks import TWEAKS
        from tweaks_manager import check_tweak, FOLDER_GUIDS

        dest = os.path.join(target_dir, "regedit_tweaks")
        os.makedirs(dest, exist_ok=True)
        ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        active_tweaks = [t for t in TWEAKS if check_tweak(t)]
        if not active_tweaks:
            return False, "Sisteminizde aktif olan bir ince ayar bulunamadı."

        reg_lines = [
            "Windows Registry Editor Version 5.00",
            "",
            "; KEYSTONE POST-FORMAT - AKTIF REGEDIT AYARLARI YEDEGI",
            f"; Olusturulma Tarihi: {ts}",
            "; Bu dosyaya cift tiklayarak da ayarlari dogrudan Windows'a uygulayabilirsiniz.",
            ""
        ]

        for t in active_tweaks:
            reg_type = t.get("reg_type")
            reg_lines.append(f"; Ayar: {t['name']} ({t['id']})")
            if reg_type == "hkcu_clsid":
                reg_lines.append(rf"[HKEY_CURRENT_USER\{t['reg_key']}]")
                reg_lines.append('@=""')
                reg_lines.append("")
            elif reg_type == "hkcu":
                reg_lines.append(rf"[HKEY_CURRENT_USER\{t['reg_key']}]")
                val_type = t.get("reg_value_type", "DWORD")
                val_data = t.get("reg_value_data", 1)
                val_name = t.get("reg_value_name", "")
                if val_type == "DWORD":
                    hex_val = hex(int(val_data))[2:].zfill(8)
                    reg_lines.append(f'"{val_name}"=dword:{hex_val}')
                else:
                    reg_lines.append(f'"{val_name}"="{val_data}"')
                reg_lines.append("")
            elif reg_type == "hklm":
                reg_lines.append(rf"[HKEY_LOCAL_MACHINE\{t['reg_key']}]")
                val_type = t.get("reg_value_type", "DWORD")
                val_data = t.get("reg_value_data", 1)
                val_name = t.get("reg_value_name", "")
                if val_type == "DWORD":
                    hex_val = hex(int(val_data))[2:].zfill(8)
                    reg_lines.append(f'"{val_name}"=dword:{hex_val}')
                else:
                    reg_lines.append(f'"{val_name}"="{val_data}"')
                reg_lines.append("")
            elif reg_type == "remove_gallery":
                reg_lines.append(r"[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\NonEnum]")
                reg_lines.append('"{e88865ea-0e1c-4e20-9aa6-edcd0212c87c}"=dword:00000001')
                reg_lines.append("")
            elif reg_type == "remove_folders_64":
                for guid in FOLDER_GUIDS:
                    reg_lines.append(rf"[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions\{guid}\PropertyBag]")
                    reg_lines.append('"ThisPCPolicy"="Hide"')
                    reg_lines.append(rf"[HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Explorer\FolderDescriptions\{guid}\PropertyBag]")
                    reg_lines.append('"ThisPCPolicy"="Hide"')
                reg_lines.append("")
            elif reg_type == "disable_location" or t["id"] == "disable_location":
                reg_lines.append(r"[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}]")
                reg_lines.append('"SensorPermissionState"=dword:00000000')
                reg_lines.append("")
                reg_lines.append(r"[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors]")
                reg_lines.append('"DisableLocation"=dword:00000001')
                reg_lines.append('"DisableLocationScripting"=dword:00000001')
                reg_lines.append('"DisableSensors"=dword:00000001')
                reg_lines.append('"DisableWindowsLocationProvider"=dword:00000001')
                reg_lines.append("")
                reg_lines.append(r"[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location]")
                reg_lines.append('"Value"="Deny"')
                reg_lines.append("")
                reg_lines.append(r"[HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location]")
                reg_lines.append('"Value"="Deny"')
                reg_lines.append("")
                reg_lines.append(r"[HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\lfsvc]")
                reg_lines.append('"Start"=dword:00000004')
                reg_lines.append("")

        reg_content = "\n".join(reg_lines)
        reg_file = os.path.join(dest, "aktif_regedit_ayarlari.reg")
        with open(reg_file, "w", encoding="utf-8") as f:
            f.write(reg_content)
        with open(os.path.join(target_dir, "aktif_regedit_ayarlari.reg"), "w", encoding="utf-8") as f:
            f.write(reg_content)

        # JSON manifest
        json_data = {
            "export_time": ts,
            "count": len(active_tweaks),
            "active_tweak_ids": [t["id"] for t in active_tweaks],
            "tweaks": [{"id": t["id"], "name": t["name"], "category": t.get("category", "")} for t in active_tweaks]
        }
        json_file = os.path.join(dest, "active_tweaks.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # Human-readable txt list
        txt_lines = [
            "=" * 78,
            "KEYSTONE - AKTİF WINDOWS REGEDIT AYARLARI RAPORU",
            f"Tarih: {ts}",
            f"Toplam Aktif Ayar: {len(active_tweaks)}",
            "=" * 78,
            ""
        ]
        for t in active_tweaks:
            txt_lines.append(f"• {t['name']} [{t['id']}] - {t.get('short_desc', '')}")
        with open(os.path.join(dest, "aktif_regedit_ayarlari.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines))

        if log_fn:
            log_fn(f"[YEDEK] {len(active_tweaks)} adet aktif regedit ayarı 'aktif_regedit_ayarlari.reg' olarak kaydedildi.")

        return True, f"{len(active_tweaks)} adet aktif regedit ayarı başarıyla yedeklendi."
    except Exception as e:
        return False, f"Regedit ayarları yedeklenirken hata: {e}"


def restore_active_tweaks(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Restore active Windows registry tweaks via Keystone manager or .reg file."""
    try:
        from data.tweaks import TWEAKS
        from tweaks_manager import apply_tweak, restart_explorer

        json_file = os.path.join(backup_dir, "active_tweaks.json")
        if not os.path.exists(json_file):
            json_file = os.path.join(backup_dir, "regedit_tweaks", "active_tweaks.json")

        reg_file = os.path.join(backup_dir, "aktif_regedit_ayarlari.reg")
        if not os.path.exists(reg_file):
            reg_file = os.path.join(backup_dir, "regedit_tweaks", "aktif_regedit_ayarlari.reg")

        if not os.path.exists(json_file) and not os.path.exists(reg_file):
            return False, "Yedek klasöründe regedit ayar yedeği bulunamadı."

        applied_count = 0
        needs_restart = False

        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            tweak_ids = set(data.get("active_tweak_ids", []))
            tweak_map = {t["id"]: t for t in TWEAKS}

            for tid in tweak_ids:
                tweak = tweak_map.get(tid)
                if tweak:
                    success, msg = apply_tweak(tweak)
                    if success:
                        applied_count += 1
                        if log_fn:
                            log_fn(f"[UYGULANDI] {tweak['name']} -> {msg}")
                        if tweak.get("needs_explorer_restart"):
                            needs_restart = True
                    else:
                        if log_fn:
                            log_fn(f"[UYARI] {tweak['name']} uygulanamadı: {msg}")

        elif os.path.exists(reg_file):
            cmd = f'reg import "{reg_file}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, **get_no_window_kwargs())
            if res.returncode == 0:
                applied_count = 1
                needs_restart = True
                if log_fn:
                    log_fn(f"[UYGULANDI] 'aktif_regedit_ayarlari.reg' sisteme başarıyla aktarıldı.")

        if needs_restart:
            if log_fn:
                log_fn("[BİLGİ] Kayıt defteri değişikliklerinin hemen geçerli olması için Gezgin yenileniyor...")
            restart_explorer()

        return True, f"{applied_count} adet kayıt defteri ayarı sisteme başarıyla uygulandı."
    except Exception as e:
        return False, f"Regedit ayarları geri yüklenirken hata: {e}"


def detect_active_tweaks_source() -> bool:
    try:
        from data.tweaks import TWEAKS
        from tweaks_manager import check_tweak
        return any(check_tweak(t) for t in TWEAKS)
    except Exception:
        return False


def detect_active_tweaks_backup(bdir: str) -> bool:
    if not bdir:
        return False
    return (
        os.path.exists(os.path.join(bdir, "aktif_regedit_ayarlari.reg")) or
        os.path.exists(os.path.join(bdir, "active_tweaks.json")) or
        os.path.exists(os.path.join(bdir, "regedit_tweaks"))
    )


def detect_installed_apps_source() -> bool:
    return True


def detect_installed_apps_backup(bdir: str) -> bool:
    if not bdir:
        return False
    return (
        os.path.exists(os.path.join(bdir, "winget_packages.json")) or
        os.path.exists(os.path.join(bdir, "installed_programs.json")) or
        os.path.exists(os.path.join(bdir, "kurulu_programlar.txt")) or
        os.path.exists(os.path.join(bdir, "installed_apps"))
    )


def backup_powershell_terminal(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Backup PowerShell profiles and Windows Terminal settings."""
    try:
        dest = os.path.join(target_dir, "terminal")
        os.makedirs(dest, exist_ok=True)
        user_dir = get_user_dir()
        local_app = get_localappdata()

        # PowerShell profile in Documents
        docs_ps = os.path.join(user_dir, "Documents", "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1")
        if os.path.exists(docs_ps):
            shutil.copy2(docs_ps, os.path.join(dest, "Microsoft.PowerShell_profile.ps1"))

        # Terminal settings
        wt_settings = os.path.join(
            local_app, "Packages", "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "LocalState", "settings.json"
        )
        if os.path.exists(wt_settings):
            shutil.copy2(wt_settings, os.path.join(dest, "windows_terminal_settings.json"))

        if log_fn:
            log_fn(f"[YEDEK] Terminal ve PowerShell yapılandırmaları '{dest}' klasörüne kopyalandı.")
        return True, "Terminal profilleri yedeklendi."
    except Exception as e:
        return False, f"Terminal yedekleme hatası: {e}"


def restore_powershell_terminal(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Restore PowerShell profiles and Windows Terminal settings."""
    try:
        src = os.path.join(backup_dir, "terminal")
        if not os.path.exists(src):
            return False, "Yedek klasöründe Terminal verisi bulunamadı."

        user_dir = get_user_dir()
        local_app = get_localappdata()

        ps_file = os.path.join(src, "Microsoft.PowerShell_profile.ps1")
        if os.path.exists(ps_file):
            dest_dir = os.path.join(user_dir, "Documents", "WindowsPowerShell")
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(ps_file, os.path.join(dest_dir, "Microsoft.PowerShell_profile.ps1"))

        wt_file = os.path.join(src, "windows_terminal_settings.json")
        if os.path.exists(wt_file):
            dest_dir = os.path.join(local_app, "Packages", "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "LocalState")
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(wt_file, os.path.join(dest_dir, "settings.json"))

        if log_fn:
            log_fn("[GERİ YÜKLE] Terminal ve PowerShell profilleri kullanıcı dizinine yüklendi.")
        return True, "Terminal profilleri geri yüklendi."
    except Exception as e:
        return False, f"Terminal geri yükleme hatası: {e}"


def backup_dev_environment(target_dir: str, log_fn=None) -> tuple[bool, str]:
    """Consolidated backup for Git, SSH, PowerShell, Terminal, and User PATH."""
    success_parts = []
    # 1. Git & SSH
    try:
        s1, m1 = backup_git_ssh(target_dir, log_fn=log_fn)
        if s1:
            success_parts.append("Git/SSH")
    except Exception as e:
        if log_fn:
            log_fn(f"[UYARI] Git/SSH hatası: {e}")

    # 2. Terminal & PowerShell
    try:
        s2, m2 = backup_powershell_terminal(target_dir, log_fn=log_fn)
        if s2:
            success_parts.append("Terminal")
    except Exception as e:
        if log_fn:
            log_fn(f"[UYARI] Terminal profilleri hatası: {e}")

    # 3. User Environment Variables (PATH)
    try:
        s3, m3 = backup_env_vars(target_dir, log_fn=log_fn)
        if s3:
            success_parts.append("PATH")
    except Exception as e:
        if log_fn:
            log_fn(f"[UYARI] Ortam değişkenleri hatası: {e}")

    if success_parts:
        return True, f"Geliştirici ortamı ({', '.join(success_parts)}) yedeklendi."
    return False, "Geliştirici profili veya ayarı bulunamadı."


def restore_dev_environment(backup_dir: str, log_fn=None) -> tuple[bool, str]:
    """Consolidated restore for Git, SSH, PowerShell, Terminal, and User PATH."""
    restored_parts = []
    # 1. Git & SSH
    try:
        s1, _ = restore_git_ssh(backup_dir, log_fn=log_fn)
        if s1:
            restored_parts.append("Git/SSH")
    except Exception:
        pass

    # 2. Terminal & PowerShell
    try:
        s2, _ = restore_powershell_terminal(backup_dir, log_fn=log_fn)
        if s2:
            restored_parts.append("Terminal")
    except Exception:
        pass

    # 3. User Environment Variables (PATH)
    try:
        s3, _ = restore_env_vars(backup_dir, log_fn=log_fn)
        if s3:
            restored_parts.append("PATH")
    except Exception:
        pass

    if restored_parts:
        return True, f"Geliştirici ortamı ({', '.join(restored_parts)}) geri yüklendi."
    return False, "Yedek klasöründe geliştirici profili bulunamadı."


# =============================================================================
# BACKUP CATALOG ITEMS (STREAMLINED MINIMAL OPTIONS)
# =============================================================================

BACKUP_ITEMS = [
    {
        "id": "browsers",
        "name": "Tarayıcı Yer İmleri (HTML & Profil)",
        "short_desc": "Brave, Chrome, Edge, Firefox vb. yer imlerini evrensel HTML ve profil yedeği olarak saklar.",
        "full_desc": "Tüm tarayıcılarınızdaki yer imlerini evrensel 'bookmarks.html' formatında dışa aktarır. Böylece format sonrası istediğiniz tarayıcıda tek tıkla 'İçe Aktar' yapabilir ya da profillerinize otomatik geri yükleyebilirsiniz.",
        "detect_source": lambda: (
            os.path.exists(os.path.join(get_localappdata(), "BraveSoftware", "Brave-Browser", "User Data")) or
            os.path.exists(os.path.join(get_localappdata(), "Google", "Chrome", "User Data")) or
            os.path.exists(os.path.join(get_localappdata(), "Microsoft", "Edge", "User Data")) or
            os.path.exists(os.path.join(get_appdata(), "Mozilla", "Firefox", "Profiles")) or
            os.path.exists(os.path.join(get_appdata(), "Opera Software", "Opera Stable")) or
            os.path.exists(os.path.join(get_localappdata(), "Vivaldi", "User Data")) or
            os.path.exists(os.path.join(get_localappdata(), "Thorium", "User Data"))
        ),
        "detect_backup": lambda bdir: (
            os.path.exists(os.path.join(bdir, "browsers")) or
            os.path.exists(os.path.join(bdir, "bookmarks.html"))
        ),
        "backup": backup_browsers,
        "restore": restore_browsers,
        "recommended": True
    },
    {
        "id": "wifi",
        "name": "Kayıtlı Wi-Fi Ağları ve Şifreleri",
        "short_desc": "Kayıtlı tüm Wi-Fi ağlarını ve şifrelerini XML olarak dışa aktarır.",
        "full_desc": "Format sonrası ev, iş veya okul Wi-Fi şifrelerini tek tek aramak zorunda kalmamanız için Windows'taki tüm kayıtlı kablosuz ağ profillerini şifreleriyle birlikte depolar ve format sonrası tek tıkla sisteme tanıtır.",
        "detect_source": lambda: True,
        "detect_backup": lambda bdir: os.path.exists(os.path.join(bdir, "wifi")),
        "backup": backup_wifi,
        "restore": restore_wifi,
        "recommended": True
    },
    {
        "id": "vscode",
        "name": "VS Code Ayarları & Eklentileri",
        "short_desc": "settings.json, keybindings, kod parçacıkları ve yüklü eklentiler listesi.",
        "full_desc": "Visual Studio Code'da özelleştirdiğiniz tema, font, editör ayarları (settings.json), kısayollar ve kurulu tüm eklentilerin listesini eksiksiz depolar ve format sonrası eklentileri otomatik yeniden kurar.",
        "detect_source": lambda: os.path.exists(os.path.join(get_appdata(), "Code", "User", "settings.json")),
        "detect_backup": lambda bdir: os.path.exists(os.path.join(bdir, "vscode")),
        "backup": backup_vscode,
        "restore": restore_vscode,
        "recommended": True
    },
    {
        "id": "dev_environment",
        "name": "Geliştirici & Terminal Profilleri (Git, SSH, Terminal, PATH)",
        "short_desc": "Git ayarları, SSH anahtarları, Terminal profilleri ve kullanıcı ortam değişkenleri.",
        "full_desc": "Yazılımcılar için kritik olan ~/.gitconfig, ~/.ssh anahtarları, Windows Terminal (settings.json), PowerShell profilleri ($PROFILE) ve Kullanıcı Ortam Değişkenlerini (User PATH) tek çatı altında eksiksiz depolar ve geri yükler.",
        "detect_source": lambda: (
            os.path.exists(os.path.join(get_user_dir(), ".gitconfig")) or
            os.path.exists(os.path.join(get_user_dir(), ".ssh")) or
            os.path.exists(os.path.join(get_user_dir(), "Documents", "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1")) or
            os.path.exists(os.path.join(get_localappdata(), "Packages", "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "LocalState", "settings.json")) or
            True
        ),
        "detect_backup": lambda bdir: (
            os.path.exists(os.path.join(bdir, "git_ssh")) or
            os.path.exists(os.path.join(bdir, "terminal")) or
            os.path.exists(os.path.join(bdir, "environment"))
        ),
        "backup": backup_dev_environment,
        "restore": restore_dev_environment,
        "recommended": True
    },
    {
        "id": "installed_apps",
        "name": "Kurulu Programlar & Uygulama Listesi (Winget & Sistem)",
        "short_desc": "Sistemde kurulu tüm programların dökümünü ve Winget paket manifestosunu yedekler.",
        "full_desc": "Bilgisayarınızdaki tüm masaüstü uygulamalarını Windows Kayıt Defteri ve Winget üzerinden tarayarak 'kurulu_programlar.txt', 'installed_programs.json' ve 'winget_packages.json' olarak depolar. Format sonrası desteklenen programları otomatik yeniden kurar veya listeyi incelemenizi sağlar.",
        "detect_source": detect_installed_apps_source,
        "detect_backup": detect_installed_apps_backup,
        "backup": backup_installed_apps,
        "restore": restore_installed_apps,
        "recommended": True
    },
    {
        "id": "active_tweaks",
        "name": "Aktif Regedit İnce Ayarları (Windows Kayıt Defteri)",
        "short_desc": "Sistemde aktif olan Windows kayıt defteri ayarlarını .reg ve JSON olarak depolar ve geri yükler.",
        "full_desc": "Keystone ve sisteminizde aktif olarak çalışan tüm Windows ince ayarlarını (klasik sağ tık menüsü, görev çubuğu 'Görevi Sonlandır', uzantıları göster vb.) doğrudan '.reg' (Kayıt Defteri) dosyası ve ayar manifestosu olarak depolar. Format sonrası tek tıkla sisteme geri uygular.",
        "detect_source": detect_active_tweaks_source,
        "detect_backup": detect_active_tweaks_backup,
        "backup": backup_active_tweaks,
        "restore": restore_active_tweaks,
        "recommended": True
    }
]


from PyQt6.QtCore import QThread, pyqtSignal


class BackupWorker(QThread):
    """Worker thread to run backup and restore operations asynchronously."""

    started_item = pyqtSignal(dict, int, int)
    output_line = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    finished_item = pyqtSignal(dict, bool, str)
    finished_all = pyqtSignal(int, int, list)

    def __init__(self, items: list[dict], mode: str, directory: str):
        super().__init__()
        self.items = items
        self.mode = mode  # "backup" or "restore"
        self.directory = directory
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total = len(self.items)
        success_count = 0
        fail_count = 0
        failed_items = []

        action_word = "Yedekleniyor" if self.mode == "backup" else "Geri Yükleniyor"
        self.output_line.emit(f"=== {action_word.upper()} İŞLEMİ BAŞLATILDI ===")
        self.output_line.emit(f"Hedef Klasör: {self.directory}")
        self.output_line.emit(f"İşlem Görecek Öğe Sayısı: {total}\n")

        for idx, item in enumerate(self.items, start=1):
            if self._is_cancelled:
                self.output_line.emit("\n[UYARI] İşlem kullanıcı tarafından durduruldu.")
                break

            self.started_item.emit(item, idx, total)
            item_name = item["name"]
            self.output_line.emit(f">>> [{idx}/{total}] {action_word}: {item_name}...")

            def log_callback(msg: str):
                self.output_line.emit(f"    {msg}")

            try:
                if self.mode == "backup":
                    success, msg = item["backup"](self.directory, log_fn=log_callback)
                else:
                    success, msg = item["restore"](self.directory, log_fn=log_callback)

                if success:
                    success_count += 1
                    self.output_line.emit(f"  [BAŞARILI] {item_name}: {msg}")
                    self.finished_item.emit(item, True, msg)
                else:
                    fail_count += 1
                    failed_items.append(f"{item_name} ({msg})")
                    self.output_line.emit(f"  [UYARI/HATA] {item_name}: {msg}")
                    self.finished_item.emit(item, False, msg)
            except Exception as e:
                fail_count += 1
                err_msg = str(e)
                failed_items.append(f"{item_name} ({err_msg})")
                self.output_line.emit(f"  [KRİTİK HATA] {item_name}: {err_msg}")
                self.finished_item.emit(item, False, err_msg)

            pct = int((idx / total) * 100)
            self.progress_percent.emit(pct)

        self.finished_all.emit(success_count, fail_count, failed_items)

