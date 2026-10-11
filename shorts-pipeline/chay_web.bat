@echo off
rem Mo trang web dieu khien + duong ham Cloudflare (de may khac vao duoc). Bam dup file nay.
rem Hai cua so den se hien ra: "Shorts web" (server) va "Cloudflare" (link truy cap). Dung tat hai cua so nay.
rem Huong dan day du: HUONG_DAN_CHAY.md
cd /d D:\videoprogenai\shorts-pipeline
set PYTHONUTF8=1

rem Giong doc VOICEVOX chay nen (khong mo cua so); buoc giong doc cung tu bat neu quen
start "" /min "%LOCALAPPDATA%\Microsoft\WinGet\Packages\HiroshibaKazuyuki.VOICEVOX.CPU_Microsoft.Winget.Source_8wekyb3d8bbwe\VOICEVOX\vv-engine\run.exe" --host 127.0.0.1 --port 50021
start "Shorts web" cmd /k "chcp 65001 >nul & python web\app.py --host 0.0.0.0"
timeout /t 4 /nobreak >nul
start "Cloudflare" cmd /k ""C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --no-autoupdate --url http://127.0.0.1:8000"

echo.
echo Da mo 2 cua so: "Shorts web" va "Cloudflare".
echo Link cho may khac: xem cua so "Cloudflare", dong co dang  https://....trycloudflare.com
echo Tren may nay: http://127.0.0.1:8000
echo.
pause
