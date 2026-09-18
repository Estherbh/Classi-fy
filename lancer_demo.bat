@echo off
rem Double-clic pour ouvrir l'interface de demonstration de Classi-fy.
rem Le chemin complet de Python evite de tomber sur une autre installation.
cd /d "%~dp0"
title Classi-fy - demo
echo.
echo   Demarrage de la demo Classi-fy...
echo   Le navigateur va s'ouvrir tout seul.
echo   Pour arreter la demo : fermez simplement cette fenetre.
echo.
"C:\Program Files\Python314\python.exe" interface_demo.py
echo.
echo   La demo s'est arretee.
pause
