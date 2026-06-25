@echo off
title CoAutomate Server
echo.
echo  ╔══════════════════════════════════════╗
echo  ║       CoAutomate - Starting...       ║
echo  ╚══════════════════════════════════════╝
echo.
echo  Open your browser at: http://localhost:8000
echo  Press Ctrl+C to stop the server.
echo.
cd /d "%~dp0backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
