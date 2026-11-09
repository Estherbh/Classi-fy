@echo off
rem Double-click to open the Classi-fy demo interface.
rem The full Python path avoids picking up another installation.
cd /d "%~dp0"
title Classi-fy - demo
echo.
echo   Starting the Classi-fy demo...
echo   The browser will open on its own.
echo   To stop the demo: just close this window.
echo.
"C:\Program Files\Python314\python.exe" demo_interface.py
echo.
echo   The demo has stopped.
pause
