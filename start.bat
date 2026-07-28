@echo off
cd /d "%~dp0"
set PORT=8080

echo 启动服务器...
start "aihot-server" python server.py

timeout /t 3 /nobreak >nul

echo 启动公网隧道...
start "aihot-tunnel" ngrok http 8080

echo.
echo === 服务已启动 ===
echo 本地: http://localhost:8080
echo 公网地址查看: http://localhost:4040
pause
