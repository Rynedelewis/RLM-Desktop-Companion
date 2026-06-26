@echo off
chcp 65001 >nul
title RLM Importer Launcher

echo.
echo RaidLootMatrix - RLM Importer Desktop GUI
echo ========================================
echo.
echo Starting RLM Importer control panel...
echo.

python "%~dp0rlm_importer_ui.py"

if errorlevel 1 (
    echo.
    echo [!] ERROR: Failed to launch RLM Importer.
    echo     Please verify that Python 3 is installed and registered in your system PATH.
    echo.
    pause
)
