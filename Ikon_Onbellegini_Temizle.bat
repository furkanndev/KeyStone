@echo off
chcp 65001 >nul
echo ============================================================
echo Windows Ikon Onbellegi (IconCache.db) Temizleyici
echo ============================================================
echo [1/3] Dosya Gezgini durduruluyor...
taskkill /f /im explorer.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [2/3] Simge onbellegi veritabanlari siliniyor...
del /f /q "%localappdata%\IconCache.db" >nul 2>&1
del /f /q "%localappdata%\Microsoft\Windows\Explorer\iconcache*" >nul 2>&1

echo [3/3] Dosya Gezgini baslatiliyor...
start explorer.exe

echo ============================================================
echo BASARILI: Gorev cubugu ve masaustu ikon onbellegi yenilendi!
echo ============================================================
timeout /t 3 >nul
