@echo off
:: Remove M+ Auto Import.bat
:: Removes all RaidLootMatrix scheduled tasks and helper scripts.
:: Run as Administrator.

chcp 65001 >nul 2>&1
echo.
echo  RaidLootMatrix Mythic+ Auto Import — Remove Scheduled Tasks
echo  ======================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Run as Administrator to remove scheduled tasks.
    pause
    exit /b 1
)

echo Removing scheduled tasks...
schtasks /delete /tn "RaidLootMatrix\M+ Import - Daily AM" /f >nul 2>&1
if %errorlevel% equ 0 (echo   Removed: M+ Import - Daily AM) else (echo   Not found: M+ Import - Daily AM)

schtasks /delete /tn "RaidLootMatrix\M+ Import - Daily PM" /f >nul 2>&1
if %errorlevel% equ 0 (echo   Removed: M+ Import - Daily PM) else (echo   Not found: M+ Import - Daily PM)

schtasks /delete /tn "RaidLootMatrix\M+ Import - At Logon" /f >nul 2>&1
if %errorlevel% equ 0 (echo   Removed: M+ Import - At Logon) else (echo   Not found: M+ Import - At Logon)

schtasks /delete /tn "RaidLootMatrix\M+ Import - WoW Watcher" /f >nul 2>&1
if %errorlevel% equ 0 (echo   Removed: M+ Import - WoW Watcher) else (echo   Not found: M+ Import - WoW Watcher)

:: Try to remove the folder (only works if empty)
schtasks /delete /tn "RaidLootMatrix" /f >nul 2>&1

echo.
echo Cleaning up script files...
set "SILENT_BAT=%~dp0raidlootmatrix_mplus_silent.bat"
set "VBS_RUN=%~dp0raidlootmatrix_mplus_run.vbs"
set "WATCHER_VBS=%~dp0raidlootmatrix_watcher_run.vbs"

if exist "%SILENT_BAT%" (
    del /f "%SILENT_BAT%" >nul 2>&1
    echo   Deleted: raidlootmatrix_mplus_silent.bat
)
if exist "%VBS_RUN%" (
    del /f "%VBS_RUN%" >nul 2>&1
    echo   Deleted: raidlootmatrix_mplus_run.vbs
)
if exist "%WATCHER_VBS%" (
    del /f "%WATCHER_VBS%" >nul 2>&1
    echo   Deleted: raidlootmatrix_watcher_run.vbs
)

echo.
echo  Done. The log file at raidlootmatrix_mplus_auto.log has been left in place.
echo.
pause
