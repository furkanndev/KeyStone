# ⚡ RetroFormat // 8-Bit Post-Format Setup & Backup Wizard ⚡

> **Windows formatı öncesi kritik ayarlarınızı (VS Code, Wi-Fi şifreleri, SSH anahtarları vb.) tek tıkla yedekleyen, format sonrasında ise DirectX, Visual C++, .NET, tarayıcılar ve geliştirici araçlarını resmi kaynaklardan kurup Windows kayıt defteri ince ayarlarını uygulayan hepsi-bir-arada masaüstü aracı.**

---

## 🎮 Temel Özellikler

- 👾 **Cyber-Retro Dark Tasarım:** Modern, göz yormayan karanlık tema ve net Segoe UI tipografisi.
- 💬 **Dinamik Üst Bilgi Paneli (Item Intel):** Fareyle üzerine gelinen her programın, ayarın veya yedekleme modülünün ne işe yaradığını en üstte anlık olarak gösterir.
- 🌐 **Sağ Tık ile Resmi Web Sayfası:** Herhangi bir program kartına sağ tıklandığında resmi indirme ve tanıtım sayfası tarayıcınızda açılır.
- 🔄 **Akıllı Seçim Kontrolü:** `[Tümünü Seç]` butonu, hepsi seçildiğinde otomatik olarak kırmızı `[Temizle]` butonuna dönüşür.

---

## 📑 3 Ana Modül / Sekmeler

### 1. 📦 Yazılım & Programlar (96 Seçkin Paket)
- **Sistem & Kütüphaneler:** DirectX End-User Runtimes, Visual C++ All-in-One (2005-2022), Microsoft .NET 8.0 Desktop Runtime, **K-Lite Codec Pack Full**, Java JDK (21/23), FFmpeg.
- **Web Tarayıcıları:** Google Chrome, Brave Browser, Mozilla Firefox, Arc Browser, Thorium Browser, Microsoft Edge, Vivaldi, Opera GX.
- **Yazılımcı Araçları & IDE:** Git, Python 3.13, Visual Studio Code, Visual Studio Community 2022, PyCharm Community, Anaconda 3, Node.js (LTS), Apache NetBeans, Eclipse IDE, MSYS2 & MinGW-w64, draw.io Desktop, Flowgorithm, Cisco Packet Tracer, Inno Setup 6, Microsoft PowerToys.
- **Veritabanı & Analiz:** SQL Server Management Studio (SSMS), PostgreSQL & pgAdmin, Microsoft Power BI Desktop.
- **Sanallaştırma:** Docker Desktop, VMware Workstation Pro, BlueStacks 5, WinCDEmu.
- **Donanım & Çevre Birimleri:** Logi Options+ (Plus), Logi Bolt, NVIDIA App, AMD Software: Adrenalin, Intel Driver & Support Assistant, G-Helper (ASUS).
- **Oyun Platformları:** Steam, Epic Games Launcher, GOG Galaxy, EA App, Ubisoft Connect, Discord.
- **Yardımcı Araçlar & Medya:** WinRAR (64-Bit), 7-Zip, Internet Download Manager (IDM), YouTube Downloader, qBittorrent, CCleaner, MKVToolNix, OBS Studio, Spotify, Telegram Desktop, Calibre, Google Quick Share, RoundedTB.

---

### 2. 🛠️ Windows İnce Ayarlar & Regedit (12 Ayar)
- **Klasik Windows 10 Sağ Tık Menüsü:** Windows 11'in hantal menüsünü kaldırıp klasik hızlı menüyü geri getirir.
- **260 Karakter Dosya Yolu Sınırını Kaldır:** `MAX_PATH` sınırını devre dışı bırakır.
- **Klasik Windows Fotoğraf Görüntüleyicisi (Photo Legacy):** Hantal Fotoğraflar uygulaması yerine efsanevi hızlı Fotoğraf Görüntüleyicisini aktif eder.
- **Bu Bilgisayar Kullanıcı Klasörlerini Kaldır:** 7 adet varsayılan klasörü Dosya Gezgininden gizler.
- **Dosya Gezgini Galeri Simgesini Kaldır:** Sol paneldeki Galeri simgesini temizler.
- **Başlat Menüsünden Bing Web Aramasını Kaldır:** Arama menüsünü ışık hızına ulaştırır.
- **Masaüstünde 'Bu Bilgisayar' İkonunu Göster:** Kaybolan simgeyi geri getirir.
- **UAC Ekran Karartmasını Kapat:** Yönetici izinlerinde ekran donmasını engeller.
- **Hazırda Bekletmeyi Kapat (hiberfil.sys):** SSD üzerinde 16-32 GB depolama alanı açar.
- **Windows Geliştirici Modunu Aç:** İmzasız araçlar ve geliştirme paketleri için izin verir.
- **Telemetri ve Tanılama Verilerini Kısıtla:** Arka plan veri gönderimini minimuma indirir.
- **Kapanış ve Yeniden Başlatma Süresini Kısalt:** Askıda kalan uygulamaları bekleme süresini düşürür.

---

### 3. 💾 Ayar Yedekleme & Geri Yükleme (Format Yardımcısı - 7 Modül)
Format öncesi verilerinizi harici diskinize veya güvenli bir klasöre tek tıkla depolar, format sonrası tek tıkla geri yükler:
1. **VS Code Ayarları & Eklentileri:** `settings.json`, `keybindings.json`, kod parçacıkları ve kurulu tüm eklentilerin listesini saklar; format sonrası eklentileri otomatik kurar.
2. **Git Yapılandırması & SSH Anahtarları:** `~/.gitconfig` kullanıcı bilgileri ve `~/.ssh` anahtarlarını güvenle taşır.
3. **Kayıtlı Wi-Fi Ağları ve Şifreleri:** Bilgisayarın bağlandığı tüm Wi-Fi ağlarını şifreleriyle XML olarak dışa aktarır ve yeni Windows'a tanıtır.
4. **Tarayıcı Yer İmleri (Chrome, Brave, Edge):** Giriş yapmasanız dahi sık kullanılanlar klasörlerinizi kopyalar.
5. **PowerShell & Windows Terminal Profilleri:** `$PROFILE` scriptlerinizi ve `settings.json` tema/kısayol ayarlarınızı korur.
6. **Kullanıcı Ortam Değişkenleri (User PATH):** Özel geliştirici yollarını ve ortam değişkenlerini JSON olarak saklar.
7. **Yüklü Programlar Manifestosu (Winget Export):** Sistemde kurulu programların tam listesini `winget_packages.json` olarak çıkartır.

---

## 🚀 Çalıştırma & Derleme

### Python ile Çalıştırma:
```powershell
python main.py
```

### Tek Dosya Taşınabilir EXE Derleme:
```powershell
python build_exe.py
```
Derleme çıktısı `dist/RetroSetup.exe` olarak üretilir. Flash belleğe atarak her format sonrası internet ve kütüphane kurulumunuzu dakikalar içinde tamamlayabilirsiniz!

