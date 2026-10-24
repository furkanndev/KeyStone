@echo off
chcp 65001 >nul
echo Keystone kapatiliyor...
taskkill /F /IM Keystone.exe >nul 2>&1
timeout /t 1 /nobreak >nul
echo Yeni sürüm kopyalanıyor...
copy /Y "%~dp0dist\Keystone.exe" "%~dp0Keystone.exe"
if %ERRORLEVEL% EQU 0 (
    echo [BASARILI] Keystone.exe basariyla guncellendi!
) else (
    echo [BILGI] Keystone.exe hala acik olabilir. Lutfen uygulamayi kapatip tekrar deneyin.
)
pause
