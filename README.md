# KeyStone 3

**Format öncesi yedek, format sonrası kurulum. Windows, macOS ve Linux'ta.**

KeyStone yeni kurulmuş bir bilgisayarı tek ekrandan hazır hale getirir:

- uygulamaları sistemin kendi paket yöneticisiyle sessizce kurar,
- işletim sistemi ince ayarlarını uygular,
- formattan önce ayarlarını tek bir (istersen şifreli) dosyaya yedekler,
- bu yedeği yeni sistemde geri yükler. Yeni sistem başka bir işletim sistemi bile olabilir.

| Sakin | Konsol |
|---|---|
| ![Sakin](docs/screenshots/calm.png) | ![Konsol](docs/screenshots/console.png) |
| **Cesur** | **Apple** |
| ![Cesur](docs/screenshots/bold.png) | ![Apple](docs/screenshots/apple.png) |

Dört görünüm stili de uygulamanın içinde, **Ayarlar → Görünüm stili** altından değiştirilebilir. Her stilin açık ve koyu teması var; vurgu rengi de ayrıca seçilebilir.

## Neler var

### Uygulamalar: 164 paketlik katalog

| Sistem | Paket yöneticisi | Katalogda |
|---|---|---|
| Windows 10/11 | winget (yedek olarak doğrudan indirme) | 151 |
| macOS | Homebrew (cask + formula) | 83 |
| Linux | apt / dnf / pacman / zypper + Flatpak + Snap | 61 |

- **Dağıtım algılama:** Ubuntu, Mint, Fedora, Arch, EndeavourOS, openSUSE ve diğerleri `/etc/os-release` üzerinden tanınır.
- **Tek şifre penceresi (Linux):** depo güncelleme ve kurulum tek bir yetkili komutta birleştirilir, böylece şifre (pkexec) bir kez sorulur.
- **Linux kaynak tercihi:** bir uygulama hem dağıtım deposunda hem Flathub'da varsa hangisinin kullanılacağı ayarlardan seçilir.
- **Hazır setler:** Temel, Geliştirici, Oyun, Yapay zekâ, Donanım, Veritabanı.
- **Kurulum betiği:** seçimi PowerShell ya da sh betiği olarak dışa aktarabilirsin.

### Sistem ayarları: anahtar anında uygular, kapatınca geri alır

- **Windows (19):** klasik sağ tık menüsü, görev çubuğunda "Görevi sonlandır", dosya uzantıları, telemetri, konum servisleri, uzun dosya yolları, hazırda bekletme ve daha fazlası.
- **macOS (15):** Finder uzantıları ve yol çubuğu, ağ/USB'ye .DS_Store yazmama, Dock gecikmesi, hızlı tuş tekrarı, ekran görüntüsü klasörü…
- **Linux (14):** GNOME koyu tema, küçült/büyüt düğmeleri, pil yüzdesi, swappiness, haftalık SSD TRIM, Flathub, ufw…

Her ayar o anki gerçek durumu okur, yani anahtarın konumu sistemde gerçekten ne olduğunu gösterir.

### Yedekle ve taşı

| Öğe | Açıklama | Geri yükleme |
|---|---|---|
| Kurulu uygulamalar | Diğer sistemde karşılıklarıyla kurulur | Tüm sistemler |
| Tarayıcı yer imleri | Chrome, Edge, Brave, Vivaldi, Opera, Arc, Firefox + her tarayıcının içe aktarabildiği tek HTML | Tüm sistemler |
| Wi-Fi ağları | Ağ adı, güvenlik türü ve parola (netsh / nmcli / networksetup) | Tüm sistemler |
| Kod editörleri | VS Code, Cursor, VSCodium, Windsurf ayarları ve eklentileri | Tüm sistemler |
| Git ve SSH | `.gitconfig`, `~/.ssh` (dosya izinleri korunur) | Tüm sistemler |
| Kabuk ve terminal | zsh/bash/fish, Neovim, tmux… ya da PowerShell ve Windows Terminal | Aynı aile |
| Ortam değişkenleri | Kullanıcı PATH'i birleştirilir, üzerine yazılmaz | Windows |
| Masaüstü ayarları | GNOME dconf / macOS Dock ve Finder | Aynı sistem |
| Yazı tipleri | Kullanıcının kurduğu yazı tipleri | Tüm sistemler |
| İnce ayarlar | Açık olan KeyStone ayarları | Aynı sistem |

- **Dosya biçimi:** yedek tek bir `.ksbak` dosyasıdır (zip + manifest). Parola verirsen dosya AES-256-GCM ile şifrelenir; anahtar parolandan scrypt ile türetilir. Yanlış parola, bozulmuş ya da kesilmiş dosya mutlaka fark edilir.
- **Mevcut dosyalar korunur:** geri yükleme var olan bir dosyanın üzerine yazmaz. Eski hali `*.keystone-old` adıyla saklanır.
- **Önce önizleme:** geri yükleme başlamadan, neyin geri yükleneceği ve hangi uygulamanın neyle eşleşeceği gösterilir. Örneğin PotPlayer yerine IINA, WinRAR yerine Keka.

### Profiller

Her profil kendi uygulama, ayar ve yedek seçimini saklar. Uygulama kimlikleri platformdan bağımsız olduğu için bir profil her işletim sisteminde çalışır. Profiller `.ksprofile` olarak dışa ve içe aktarılabilir. KeyStone 2.x profilleri ilk açılışta otomatik olarak taşınır.

## Kurulum

[Releases](../../releases) sayfasından kendi sistemine uygun dosyayı indir:

- **Windows:** `KeyStone-windows-x64.exe`. Microsoft Store'dan gelen *App Installer* (winget) gerekir.
- **macOS:** `KeyStone-macos-arm64.zip` (Apple silicon) ya da `-x64.zip` (Intel). Homebrew yoksa önce <https://brew.sh> adresinden kur. Uygulama imzasız olduğu için ilk açılışta Finder'da sağ tık → **Aç** de.
- **Linux:** `keystone-linux-x64` dosyasını indir, `chmod +x` ile çalıştırılabilir yap ve çalıştır. Pencere için WebKitGTK gerekir (`gir1.2-webkit2-4.1`). WebKitGTK yoksa KeyStone kendiliğinden tarayıcıda açılır.

### Kaynaktan çalıştırma

```bash
python -m pip install -e ".[gui]"      # Python 3.10+
python -m keystone                     # yerel pencere
python -m keystone --serve             # tarayıcıda (127.0.0.1, tek kullanımlık anahtarla)
```

Linux'ta pencere için ayrıca `sudo apt install python3-gi gir1.2-webkit2-4.1` gerekir (ya da dağıtımındaki karşılığı).

### Komut satırı

Her şey arayüz olmadan da yapılabilir:

```bash
keystone info                                  # algılanan sistem ve paket yöneticileri
keystone list --installed
keystone install vscode git firefox
keystone profile Geliştirici install
keystone backup -o /media/usb --password       # şifreli yedek
keystone restore yedek.ksbak --password --plan # yalnızca ne olacağını göster
keystone tweaks apply show_file_extensions dark_mode
```

## Mimari

```
keystone/
  core/        sistem algılama, yollar, süreç çalıştırma (iptal + yetki yükseltme)
  pkg/         winget · brew · apt · dnf · pacman · zypper · flatpak · snap + çözümleyici
  tweaks/      bildirimsel ince ayar motoru (registry / defaults / gsettings / dosya / komut)
  backup/      .ksbak arşivi, akış halinde şifreleme, yedek öğeleri
  data/        catalog.json: tek kaynak, platform başına paket kimlikleri
  ui/          HTML/CSS/JS arayüz (derleme adımı yok), 4 stil × açık/koyu, TR/EN
  api.py       arayüzün çağırdığı tek yüzey
  jobs.py      görev kuyruğu + canlı olay akışı
  app.py       pywebview penceresi (WebView2 / WKWebView / WebKitGTK)
  server.py    tarayıcı modu (yalnızca 127.0.0.1, Host denetimi, anahtar zorunlu)
```

- **Neden pywebview:** Electron gibi bir tarayıcı paketlenmez, her işletim sisteminin kendi web motoru kullanılır. Bu sayede dosya küçük kalır, uygulama hızlı açılır ve 2.x'teki Python mantığı yeniden kullanılır.
- **Neden derleme adımı yok:** arayüz düz HTML/CSS/JS olduğu için geliştirmek ya da derlemek için Node.js gerekmez.

## Geliştirme

```bash
python -m pip install -e ".[dev]"
python -m pytest            # testler hiçbir zaman gerçek paket yöneticisine dokunmaz
python tools/build.py       # bu işletim sistemi için tek dosyalık sürüm
```

`v*` biçiminde bir etiket gönderildiğinde GitHub Actions şunları yapar:

1. testleri Windows, macOS ve Ubuntu'da çalıştırır,
2. dört ayrı derleme üretir (Windows x64, macOS arm64, macOS x64, Linux x64),
3. bunları bir GitHub sürümüne ekler.

## Lisans

MIT
