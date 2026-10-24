# Keystone

**Automated Post-Installation Deployment, System Optimization, and Configuration Migration Platform for Windows**

[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20x64-0078D6?style=flat-square)](https://microsoft.com/windows)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=flat-square)](https://python.org)
[![Framework: PyQt6](https://img.shields.io/badge/GUI-PyQt6%20Native-41CD52?style=flat-square)](https://riverbankcomputing.com/software/pyqt/)
[![Release: Latest](https://img.shields.io/badge/Release-v1.0.0-0078D6?style=flat-square)](https://github.com/furkanndev/Keystone/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## Overview

Keystone is a standalone desktop utility engineered to streamline and automate the setup process following a clean Windows installation. It consolidates silent software installation, performance-oriented Windows registry tweaks, and full-spectrum configuration backup/migration into an integrated, portable solution.

Built with native PyQt6 without external webview wrappers, Keystone provides high responsiveness, low memory overhead, and dark/light design systems inspired by macOS human interface guidelines.

---

## Interface Previews

### Software Catalog & Package Deployment (Dark Mode)
![Software Catalog](assets/screenshots/preview_apps.png)

### Windows Registry Optimizations (Dark Mode)
![Registry Tweaks](assets/screenshots/preview_tweaks.png)

### Configuration Backup & System Migration (Dark Mode)
![Backup & Migration](assets/screenshots/preview_backup.png)

### Light Mode Theme
![Light Mode Theme](assets/screenshots/preview_light.png)

---

## Core Capabilities

### 1. Curated Software Deployment Engine
- **Direct & Silent Provisioning**: Automates installation via Windows Package Manager (Winget) and direct vendor installers with silent argument flags (`/S`, `/VERYSILENT`, `/qn`).
- **Comprehensive Ecosystem**: Categorized selection across Essential Runtimes (DirectX, VC++ All-in-One 2005-2022, .NET), Web Browsers, Development Tools (Git, Python, VS Code, JetBrains, Docker, Node.js), Artificial Intelligence & LLM clients, Security suites, and Multimedia.
- **Dynamic Package Detection**: Automatically queries local package databases and system uninstall hives on startup to indicate installed applications.
- **Top Intelligence Panel**: Displays package descriptions, download sources, categories, and one-click official website redirection.

### 2. Validated Windows Registry Optimizations
- **Productivity & Interface Tweaks**: Restores Windows 10 Classic Context Menu on Windows 11, enables Taskbar "End Task" on right-click, removes Explorer duplicate folders, and restores the classic Windows Photo Viewer.
- **Telemetry & Resource Management**: Minimizes diagnostic telemetry, disables Bing search injection in Start Menu, disables hibernation file (`hiberfil.sys`) to recover disk space, and speeds up system shutdown timeouts.
- **Real-Time State Validation**: Actively inspects Windows Registry hives (`HKCU` and `HKLM`) to report live configuration states and synchronizes selection states automatically.
- **Explorer Shell Refresh**: Automatically notifies Windows Shell (`SHChangeNotify`) and restarts `explorer.exe` safely when context menu or shell-level modifications require immediate activation.

### 3. Pre-Format Backup & Post-Format Migration
- **Browser Bookmarks & Profiles**: Exports universal Netscape `bookmarks.html` and profile configurations across Chromium browsers (Chrome, Brave, Edge, Opera, Vivaldi, Thorium) and Mozilla Firefox.
- **Wi-Fi Network Credentials**: Exports all saved wireless network security profiles to XML and restores them on fresh installations.
- **Developer Workspaces**: Consolidates `~/.gitconfig`, `~/.ssh` keys, Windows Terminal configuration (`settings.json`), PowerShell profiles (`$PROFILE`), and User `PATH` environment variables.
- **VS Code Configuration**: Backs up user settings, custom keybindings, snippets, and installed extension lists with automated reinstallation.
- **Installed Software Inventory**: Generates structured `installed_programs.json` and `kurulu_programlar.txt` reports along with `winget_packages.json` export manifests for one-click re-deployment.
- **Active Registry Tweaks**: Generates valid `aktif_regedit_ayarlari.reg` files and JSON manifests to re-apply personalized optimizations seamlessly.

### 4. Isolated Multi-Profile Architecture
- **Browser-Style Profiles**: Independent user profiles allowing distinct application selections, optimization lists, and backup paths.
- **Portable Persistence**: Stores configuration in `profiles.json` adjacent to the executable or in `%APPDATA%/Keystone` when installed.

---

## Architecture and Repository Structure

```
Keystone/
|-- assets/               # Interface vectors, monochrome icons, switches, branding
|-- data/
|   |-- packages.py       # Package catalog, winget IDs, silent flags, categories
|   |-- tweaks.py         # Registry optimizations, hive definitions, key values
|-- installer.py          # Multithreaded background download & installation worker
|-- tweaks_manager.py     # Registry read/write engine, Explorer shell hooks
|-- backup_manager.py     # Backup & restore operations, manifest generation
|-- profile_manager.py    # Multi-profile workspace manager and persistence
|-- styles.py             # Qt Style Sheets (QSS) design system (Dark & Light)
|-- ui_main.py            # Primary window layout, navigation rail, HUD intelligence
|-- ui_card.py            # Package card widget with Apple-style toggle switch
|-- ui_tweak_card.py      # Registry tweak card widget
|-- ui_backup_card.py     # Backup and recovery item widget
|-- ui_profile_card.py    # Profile management widgets
|-- ui_profile_menu.py    # Contextual profile actions
|-- build_exe.py          # PyInstaller standalone binary compilation script
|-- main.py               # Application entry point and DPI scaling configuration
|-- utils.py              # Administrative privilege checks and shell helpers
|-- .gitignore            # Clean git exclusion rules
|-- README.md             # Project documentation
```

---

## Installation & Execution

### Standalone Executable (Releases)
Pre-compiled standalone binaries with all runtime dependencies bundled are published under GitHub Releases:
- **Download Latest**: [Keystone.exe (Direct Download)](https://github.com/furkanndev/Keystone/releases/latest/download/Keystone.exe)
- **Release History**: [GitHub Releases Page](https://github.com/furkanndev/Keystone/releases)

No Python installation or dependencies required. Run directly as Administrator.

### Prerequisites (For Running from Source)
- Windows 10 (Build 19041+) or Windows 11 (64-bit).
- Python 3.11 or higher.
- Administrative permissions (required for Visual C++, DirectX, and system-wide registry modifications).

### Running from Source
1. Clone the repository:
   ```powershell
   git clone https://github.com/furkanndev/Keystone.git
   cd Keystone
   ```

2. Install dependencies:
   ```powershell
   pip install PyQt6
   ```

3. Launch Keystone:
   ```powershell
   python main.py
   ```

### Building the Standalone Executable
To produce a portable `.exe` with all resources bundled:
```powershell
python build_exe.py
```
The compiled binary will be placed at `dist/Keystone.exe` and copied to the root project directory.

---

## Keyboard Shortcuts

| Shortcut | Scope | Action |
|:---|:---|:---|
| `Ctrl+A` | Active Category / Tab | Select all / Deselect all visible items |
| `Ctrl+F` | Global | Focus search input bar |
| `Ctrl+T` | Global | Toggle Dark / Light theme |
| `Escape` | Global | Clear search query or return to default view |

---

## Türkçe Açıklama ve Özellikler

Keystone, Windows formatı sonrasında bilgisayarın baştan kurulum sürecini otomatikleştiren profesyonel bir masaüstü aracıdır.

- **Yazılım Kurulumu**: DirectX, Visual C++, .NET, tarayıcılar, geliştirici SDK'ları ve popüler yazılımları resmi kaynaklardan sessizce kurar.
- **Kayıt Defteri (Regedit) Ayarları**: Windows 11 klasik sağ tık menüsü, görev çubuğu 'Görevi Sonlandır', telemetri engelleme ve hızlandırma ayarlarını sistem durumuna göre otomatik algılar ve uygular.
- **Yedekleme & Geri Yükleme**: Format öncesi Wi-Fi şifrelerini, tarayıcı yer imlerini, VS Code konfigürasyonlarını, SSH anahtarlarını, kurulu program listesini ve aktif kayıt defteri ayarlarını tek tıkla depolar ve format sonrasında eksiksiz geri yükler.
- **Yönetici Hakları**: İlgili sistem kütüphaneleri ve Windows servisleri için UAC haklarını şeffaf ve güvenli bir şekilde yönetir.

---

## License

This project is licensed under the [MIT License](LICENSE).
