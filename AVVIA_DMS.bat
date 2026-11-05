@echo off
title DMS - Developments Management System
cd /d "%~dp0\dms_app"
python run_dms.py
if errorlevel 1 (
    echo.
    echo Si e' verificato un errore durante l'avvio di DMS.
    pause
)
