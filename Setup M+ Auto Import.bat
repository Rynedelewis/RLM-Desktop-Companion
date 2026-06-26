@echo off
:: Setup M+ Auto Import.bat
:: Run this ONCE to register two Windows Scheduled Tasks:
::   1. Every 12 hours
::   2. 5 minutes after you log in
:: Tasks run silently in the background and log to raidlootmatrix_mplus_auto.log
:: To remove: run "Remove M+ Auto Import.bat"

chcp 65001 >nul 2>&1
echo.
echo  RaidLootMatrix Mythic+ Auto Import — Task Scheduler Setup
echo  ====================================================
echo.

:: Resolve paths
set SILENT_BAT=%~dp0raidlootmatrix_mplus_silent.bat
set TASK_FOLDER=RaidLootMatrix

:: Check if running as admin (schtasks /create requires it for some configs)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] This script needs to run as Administrator to create scheduled tasks.
    echo      Right-click "Setup M+ Auto Import.bat" and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)

:: ── Task 1: Daily at 6:00 AM (local time / CST) ─────────────────────────
echo  [1/3] Creating task: Daily at 6:00 AM...
schtasks /create ^
  /tn "%TASK_FOLDER%\M+ Import - Daily 6AM" ^
  /tr "cmd.exe /c \"%SILENT_BAT%\"" ^
  /sc DAILY /st 06:00 ^
  /ru "%USERNAME%" ^
  /it ^
  /f
if %errorlevel% equ 0 (
    echo       OK — will run every day at 6:00 AM.
) else (
    echo       FAILED — check that you are running as Administrator.
)

echo.

:: ── Task 2: Daily at 6:00 PM ─────────────────────────────────────────────
echo  [2/3] Creating task: Daily at 6:00 PM...
schtasks /create ^
  /tn "%TASK_FOLDER%\M+ Import - Daily 6PM" ^
  /tr "cmd.exe /c \"%SILENT_BAT%\"" ^
  /sc DAILY /st 18:00 ^
  /ru "%USERNAME%" ^
  /it ^
  /f
if %errorlevel% equ 0 (
    echo       OK — will run every day at 6:00 PM.
) else (
    echo       FAILED — check that you are running as Administrator.
)

echo.

:: ── Task 3: At logon + 5 minute delay ────────────────────────────────────
echo  [3/3] Creating task: At logon (5 min delay)...
schtasks /create ^
  /tn "%TASK_FOLDER%\M+ Import - At Logon" ^
  /tr "cmd.exe /c \"%SILENT_BAT%\"" ^
  /sc ONLOGON ^
  /delay 0005:00 ^
  /ru "%USERNAME%" ^
  /it ^
  /f
if %errorlevel% equ 0 (
    echo       OK — will run 5 minutes after you log into Windows.
) else (
    echo       FAILED — check that you are running as Administrator.
)

echo.
echo  ====================================================
echo  Setup complete!
echo.
echo  To VIEW task status:
echo    Open Task Scheduler ^> Task Scheduler Library ^> RaidLootMatrix
echo.
echo  To VIEW the log:
echo    Open: %~dp0raidlootmatrix_mplus_auto.log
echo.
echo  To STOP / remove tasks:
echo    Run: Remove M+ Auto Import.bat
echo.
echo  SCHEDULE:
echo    Daily 6:00 AM  ^— every morning (catches overnight reset data)
echo    At logon       ^— 5 minutes after you log into Windows
echo.
pause
