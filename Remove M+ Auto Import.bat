@echo off
:: Remove M+ Auto Import.bat
:: Removes both RaidLootMatrix scheduled tasks from Windows Task Scheduler.
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

schtasks /delete /tn "RaidLootMatrix\M+ Import - Daily 6AM" /f
if %errorlevel% equ 0 (echo   Removed: M+ Import - Daily 6AM) else (echo   Not found: M+ Import - Daily 6AM)

schtasks /delete /tn "RaidLootMatrix\M+ Import - Daily 6PM" /f
if %errorlevel% equ 0 (echo   Removed: M+ Import - Daily 6PM) else (echo   Not found: M+ Import - Daily 6PM)

schtasks /delete /tn "RaidLootMatrix\M+ Import - At Logon" /f
if %errorlevel% equ 0 (echo   Removed: M+ Import - At Logon) else (echo   Not found: M+ Import - At Logon)

:: Try to remove the folder (only works if empty)
schtasks /delete /tn "RaidLootMatrix" /f >nul 2>&1

echo.
echo  Done. The log file at raidlootmatrix_mplus_auto.log has been left in place.
echo.
pause
