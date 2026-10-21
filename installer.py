"""
RetroFormat Installation Engine
Executes official package installations via Winget with real-time logging,
status updates, and background scanning.
"""

import sys
import os
import subprocess
import re
import ctypes
import ssl
import urllib.request
import urllib.parse
from PyQt6.QtCore import QThread, pyqtSignal


def clean_yaml_manifests(target_dir: str):
    """Remove any .yaml and .yml manifest files created by winget in the download directory."""
    if not target_dir or not os.path.isdir(target_dir):
        return
    try:
        for root, dirs, files in os.walk(target_dir, topdown=False):
            for file in files:
                if file.lower().endswith((".yaml", ".yml")):
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception:
                        pass
            if root != target_dir:
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                except Exception:
                    pass
    except Exception:
        pass


def is_admin() -> bool:
    """Check if the current process has administrative privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin():
    """Restart current application with administrative elevation."""
    if is_admin():
        return True
    try:
        script = sys.argv[0]
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    except Exception as e:
        print("Elevation failed:", e)
        return False


class InstalledScanner(QThread):
    """Background worker to detect already installed software via winget."""
    scan_complete = pyqtSignal(set)

    def run(self):
        installed_ids = set()
        try:
            # Run winget list once
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            res = subprocess.run(
                ["winget", "list"],
                capture_output=True,
                text=True,
                errors="replace",
                shell=True,
                startupinfo=startupinfo
            )
            if res.returncode == 0 or res.stdout:
                output = res.stdout
                for line in output.splitlines():
                    parts = line.split()
                    for part in parts:
                        part_clean = part.strip()
                        # Match valid package IDs with dots and letters, excluding pure versions
                        if "." in part_clean and len(part_clean) > 4 and not re.match(r"^[\d\.\-_]+$", part_clean):
                            installed_ids.add(part_clean.lower())
        except Exception as e:
            print("Scan error:", e)

        self.scan_complete.emit(installed_ids)


class InstallWorker(QThread):
    """Background worker that sequentially downloads and installs selected packages."""

    # Signals for UI communication
    started_package = pyqtSignal(dict, int, int)      # (pkg, index, total)
    output_line = pyqtSignal(str, str)                 # (pkg_id, line)
    progress_percent = pyqtSignal(int, int)            # (overall_percent, current_pkg_percent)
    finished_package = pyqtSignal(dict, bool, str)     # (pkg, success, message)
    finished_all = pyqtSignal(int, int, list)          # (success_count, fail_count, failed_names)

    def __init__(self, packages_to_install: list, mode: str = "install", download_dir: str = ""):
        super().__init__()
        self.packages = packages_to_install
        self.mode = mode
        self.download_dir = download_dir
        self._is_cancelled = False
        self._current_process = None

    def cancel(self):
        """Cancel remaining operations cleanly by terminating process tree."""
        self._is_cancelled = True
        if self._current_process:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        f"taskkill /F /T /PID {self._current_process.pid}",
                        shell=True,
                        capture_output=True
                    )
                else:
                    self._current_process.terminate()
            except Exception:
                pass

    def run(self):
        total = len(self.packages)
        success_count = 0
        fail_count = 0
        failed_items = []

        percent_pattern = re.compile(r"(\d{1,3})%")

        if self.mode == "download" and self.download_dir:
            try:
                os.makedirs(self.download_dir, exist_ok=True)
            except Exception:
                pass

        action_title = "Kurulum" if self.mode == "install" else "Setup İndirme"

        for idx, pkg in enumerate(self.packages):
            if self._is_cancelled:
                self.output_line.emit("system", f"[DURDURULDU] {action_title} kullanıcı tarafından durduruldu.")
                break

            pkg_id = pkg["id"]
            pkg_name = pkg["name"]
            winget_id = pkg["winget_id"]

            self.started_package.emit(pkg, idx + 1, total)
            self.output_line.emit(pkg_id, "=" * 55)
            self.output_line.emit(pkg_id, f"[{'KURULUYOR' if self.mode == 'install' else 'INDIRILIYOR'}] [{idx + 1}/{total}] {pkg_name}")
            self.output_line.emit(pkg_id, f"[KAYNAK ID] {winget_id}")
            if self.mode == "download":
                self.output_line.emit(pkg_id, f"[HEDEF KLASOR] {self.download_dir}")

            # Overall progress calculation
            overall_pct = int((idx / total) * 100)
            self.progress_percent.emit(overall_pct, 0)

            # Build winget command
            if self.mode == "download":
                cmd = [
                    "winget", "download",
                    "--id", winget_id,
                    "-d", self.download_dir,
                    "--exact",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--disable-interactivity"
                ]
            else:
                cmd = [
                    "winget", "install",
                    "--id", winget_id,
                    "--exact",
                    "--silent",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--disable-interactivity"
                ]

            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            pkg_success = False
            error_msg = ""

            try:
                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace",
                    shell=True,
                    startupinfo=startupinfo
                )

                last_percent = 0
                for line in iter(self._current_process.stdout.readline, ""):
                    if self._is_cancelled:
                        break

                    clean_line = line.strip()
                    if not clean_line:
                        continue

                    # Send to live terminal log
                    self.output_line.emit(pkg_id, clean_line)

                    # Try to extract download percentage
                    match = percent_pattern.search(clean_line)
                    if match:
                        try:
                            pct = int(match.group(1))
                            if 0 <= pct <= 100 and pct != last_percent:
                                last_percent = pct
                                current_overall = int(((idx + (pct / 100.0)) / total) * 100)
                                self.progress_percent.emit(min(99, current_overall), pct)
                        except Exception:
                            pass

                self._current_process.wait()
                return_code = self._current_process.returncode

                # Winget return codes: 0 = success, -1978335189 = already installed / no applicable update
                if return_code in [0, 2316632067, -1978335189]:
                    pkg_success = True
                    error_msg = "Setup Klasöre İndirildi" if self.mode == "download" else "Başarıyla Kuruldu"
                elif self.mode == "install" and ("Already installed" in error_msg or return_code == -1978335212):
                    pkg_success = True
                    error_msg = "Zaten Sistemde Kurulu"
                else:
                    # Check fallback winget IDs if any
                    fallbacks = pkg.get("fallback_winget_ids", [])
                    if fallbacks and not self._is_cancelled:
                        self.output_line.emit(pkg_id, f"[UYARI] Alternatif paket deneniyor...")
                        for alt_id in fallbacks:
                            if self.mode == "download":
                                alt_cmd = [
                                    "winget", "download", "--id", alt_id,
                                    "-d", self.download_dir,
                                    "--exact",
                                    "--accept-package-agreements", "--accept-source-agreements",
                                    "--disable-interactivity"
                                ]
                            else:
                                alt_cmd = [
                                    "winget", "install", "--id", alt_id,
                                    "--exact", "--silent",
                                    "--accept-package-agreements", "--accept-source-agreements"
                                ]
                            alt_res = subprocess.run(
                                alt_cmd,
                                capture_output=True,
                                text=True,
                                errors="replace",
                                shell=True,
                                startupinfo=startupinfo
                            )
                            if alt_res.returncode == 0:
                                pkg_success = True
                                error_msg = "Setup Alternatif ID ile İndirildi" if self.mode == "download" else "Alternatif ID ile Kuruldu"
                                break

                    if not pkg_success:
                        # Fallback to direct download URL if defined
                        direct_url = pkg.get("direct_download_url")
                        if direct_url and not self._is_cancelled:
                            self.output_line.emit(pkg_id, f"[ALTERNATİF] Resmi sunucudan doğrudan indiriliyor: {direct_url}")
                            direct_ok, direct_msg = self._download_direct(pkg, direct_url, idx, total)
                            if direct_ok:
                                pkg_success = True
                                error_msg = "Resmi Sunucudan İndirildi" if self.mode == "download" else "Doğrudan İndirilip Kuruldu"
                            else:
                                error_msg = direct_msg
                        else:
                            error_msg = f"Hata Kodu: {return_code}"

            except Exception as e:
                pkg_success = False
                error_msg = str(e)
                self.output_line.emit(pkg_id, f"[HATA] {error_msg}")

            if self.mode == "download":
                self._clean_yaml_manifests()

            if pkg_success:
                success_count += 1
                self.output_line.emit(pkg_id, f"[TAMAMLANDI] {pkg_name} ({error_msg})\n")
                self.finished_package.emit(pkg, True, error_msg)
            else:
                fail_count += 1
                failed_items.append(pkg_name)
                self.output_line.emit(pkg_id, f"[BASARISIZ] {pkg_name} ({error_msg})\n")
                self.finished_package.emit(pkg, False, error_msg)

        if self.mode == "download":
            self._clean_yaml_manifests()

        final_pct = 100 if not self._is_cancelled else int((success_count / max(1, total)) * 100)
        self.progress_percent.emit(final_pct, 100)
        self.finished_all.emit(success_count, fail_count, failed_items)

    def _clean_yaml_manifests(self):
        """Remove any .yaml and .yml manifest files created by winget in the download directory."""
        if self.download_dir:
            clean_yaml_manifests(self.download_dir)

    def _download_direct(self, pkg: dict, url: str, idx: int, total: int) -> tuple[bool, str]:
        """Download file directly via HTTP/HTTPS with chunked streaming and progress reporting."""
        pkg_id = pkg["id"]
        pkg_name = pkg["name"]

        target_dir = self.download_dir if self.mode == "download" else os.path.join(
            os.environ.get("TEMP", "C:\\Temp"), "RetroSetup_Install"
        )
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception:
            pass

        parsed_url = urllib.parse.urlparse(url)
        url_filename = os.path.basename(parsed_url.path)
        if not url_filename or "." not in url_filename:
            url_filename = f"{pkg_id}_setup.exe"
        url_filename = re.sub(r'[\\/*?:"<>|]', "", url_filename)

        dest_path = os.path.join(target_dir, url_filename)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": pkg.get("website", "") or "https://www.google.com"
        }

        ssl_ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers=headers)

        try:
            try:
                response = urllib.request.urlopen(req, context=ssl_ctx, timeout=30)
            except (ssl.SSLError, urllib.error.URLError):
                unverified_ctx = ssl._create_unverified_context()
                response = urllib.request.urlopen(req, context=unverified_ctx, timeout=30)

            with response:
                cd = response.headers.get("Content-Disposition", "")
                if cd and "filename=" in cd:
                    fname_match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)', cd)
                    if fname_match:
                        raw_fname = fname_match.group(1).strip()
                        raw_fname = re.sub(r'[\\/*?:"<>|]', "", raw_fname)
                        if raw_fname:
                            dest_path = os.path.join(target_dir, raw_fname)

                content_len = response.headers.get("Content-Length")
                total_bytes = int(content_len) if content_len and content_len.isdigit() else 0

                filename_display = os.path.basename(dest_path)
                self.output_line.emit(pkg_id, f"[DOĞRUDAN İNDİRME] '{filename_display}' kaydediliyor...")

                downloaded_bytes = 0
                chunk_size = 128 * 1024
                last_reported_pct = -1

                with open(dest_path, "wb") as f_out:
                    while True:
                        if self._is_cancelled:
                            f_out.close()
                            if os.path.exists(dest_path):
                                try:
                                    os.remove(dest_path)
                                except Exception:
                                    pass
                            return False, "Kullanıcı tarafından iptal edildi"

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        downloaded_bytes += len(chunk)

                        if total_bytes > 0:
                            current_pkg_pct = int((downloaded_bytes / total_bytes) * 100)
                            if current_pkg_pct != last_reported_pct and current_pkg_pct % 5 == 0:
                                last_reported_pct = current_pkg_pct
                                current_overall = int(((idx + (current_pkg_pct / 100.0)) / total) * 100)
                                self.progress_percent.emit(min(99, current_overall), current_pkg_pct)
                                mb_down = downloaded_bytes / (1024 * 1024)
                                mb_total = total_bytes / (1024 * 1024)
                                self.output_line.emit(pkg_id, f"İndiriliyor: %{current_pkg_pct} ({mb_down:.1f} MB / {mb_total:.1f} MB)")

            if self.mode == "install":
                self.output_line.emit(pkg_id, f"[KURULUM] Kurulum dosyası çalıştırılıyor: {filename_display}")
                if dest_path.lower().endswith(".msi"):
                    run_cmd = f'msiexec /i "{dest_path}" /quiet /norestart'
                else:
                    silent_args = " ".join(pkg.get("silent_args", ["/S", "/silent", "/q"]))
                    run_cmd = f'"{dest_path}" {silent_args}'
                res = subprocess.run(run_cmd, shell=True)
                if res.returncode == 0:
                    return True, "Başarıyla Kuruldu"
                else:
                    return False, f"Kurulum Hata Kodu: {res.returncode}"

            return True, "Setup İndirildi"

        except Exception as e:
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            return False, f"Doğrudan İndirme Hatası: {str(e)}"
