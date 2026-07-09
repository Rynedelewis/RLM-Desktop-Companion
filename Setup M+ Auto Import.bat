@echo off
:: Setup M+ Auto Import.bat
:: Run this ONCE to register four Windows Scheduled Tasks:
::   1. Daily AM Scan (6:00 AM)
::   2. Daily PM Scan (6:00 PM)
::   3. 5 minutes after you log in
::   4. WoW Close Watcher (runs in background, syncs when WoW closes)
:: Tasks run silently in the background and log to raidlootmatrix_mplus_auto.log
:: To remove: run "Remove M+ Auto Import.bat"

chcp 65001 >nul 2>&1
echo.
echo  RaidLootMatrix Mythic+ Auto Import — Task Scheduler Setup
echo  ====================================================
echo.

:: Resolve paths
set SILENT_BAT=%~dp0raidlootmatrix_mplus_silent.bat
set VBS_RUN=%~dp0raidlootmatrix_mplus_run.vbs
set WATCHER_VBS=%~dp0raidlootmatrix_watcher_run.vbs
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

:: Generate raidlootmatrix_mplus_silent.bat dynamically
echo Generating silent runner batch script...
echo @echo off > "%SILENT_BAT%"
echo set RAIDLOOTMATRIX_SCHEDULED=1 >> "%SILENT_BAT%"
echo if exist "%~dp0RLM_Companion.exe" ( >> "%SILENT_BAT%"
echo     "%~dp0RLM_Companion.exe" --run-mplus --week both ^> "%~dp0raidlootmatrix_mplus_auto.log" 2^>^&1 >> "%SILENT_BAT%"
echo     "%~dp0RLM_Companion.exe" --run-sync --non-interactive ^>^> "%~dp0raidlootmatrix_mplus_auto.log" 2^>^&1 >> "%SILENT_BAT%"
echo ) else ( >> "%SILENT_BAT%"
echo     pythonw "%~dp0raidlootmatrix_mplus.py" --week both ^> "%~dp0raidlootmatrix_mplus_auto.log" 2^>^&1 >> "%SILENT_BAT%"
echo     pythonw "%~dp0rlm_discord_sync.py" --non-interactive ^>^> "%~dp0raidlootmatrix_mplus_auto.log" 2^>^&1 >> "%SILENT_BAT%"
echo ) >> "%SILENT_BAT%"

:: Generate raidlootmatrix_mplus_run.vbs dynamically
echo Generating silent VBScript wrapper...
echo Dim shell, fso, scriptDir, bat > "%VBS_RUN%"
echo Set shell = CreateObject("WScript.Shell") >> "%VBS_RUN%"
echo Set fso = CreateObject("Scripting.FileSystemObject") >> "%VBS_RUN%"
echo scriptDir = fso.GetParentFolderName(WScript.ScriptFullName) >> "%VBS_RUN%"
echo bat = scriptDir ^& "\raidlootmatrix_mplus_silent.bat" >> "%VBS_RUN%"
echo shell.Run "cmd.exe /c """ ^& bat ^& """", 0, True >> "%VBS_RUN%"
echo Set shell = Nothing >> "%VBS_RUN%"
echo Set fso = Nothing >> "%VBS_RUN%"

:: Generate raidlootmatrix_watcher_run.vbs dynamically
echo Generating WoW Watcher VBScript wrapper...
echo Dim shell, fso, scriptDir, exe > "%WATCHER_VBS%"
echo Set shell = CreateObject("WScript.Shell") >> "%WATCHER_VBS%"
echo Set fso = CreateObject("Scripting.FileSystemObject") >> "%WATCHER_VBS%"
echo scriptDir = fso.GetParentFolderName(WScript.ScriptFullName) >> "%WATCHER_VBS%"
echo If fso.FileExists(scriptDir ^& "\RLM_Companion.exe") Then >> "%WATCHER_VBS%"
echo     exe = """" ^& scriptDir ^& "\RLM_Companion.exe"" --watch-wow" >> "%WATCHER_VBS%"
echo Else >> "%WATCHER_VBS%"
echo     exe = "pythonw """ ^& scriptDir ^& "\rlm_importer_ui.py"" --watch-wow" >> "%WATCHER_VBS%"
echo End If >> "%WATCHER_VBS%"
echo shell.Run exe, 0, False >> "%WATCHER_VBS%"
echo Set shell = Nothing >> "%WATCHER_VBS%"
echo Set fso = Nothing >> "%WATCHER_VBS%"

echo.

:: ── Task 1: Daily at 6:00 AM ─────────────────────────────────────────────
echo  [1/4] Creating task: Daily at 6:00 AM...
schtasks /create ^
  /tn "%TASK_FOLDER%\M+ Import - Daily AM" ^
  /tr "wscript.exe \"%VBS_RUN%\"" ^
  /sc DAILY /st 06:00 ^
  /f
if %errorlevel% equ 0 (
    echo       OK — will run every day at 6:00 AM.
) else (
    echo       FAILED to create Daily AM task.
)

echo.

:: ── Task 2: Daily at 6:00 PM ─────────────────────────────────────────────
echo  [2/4] Creating task: Daily at 6:00 PM...
schtasks /create ^
  /tn "%TASK_FOLDER%\M+ Import - Daily PM" ^
  /tr "wscript.exe \"%VBS_RUN%\"" ^
  /sc DAILY /st 18:00 ^
  /f
if %errorlevel% equ 0 (
    echo       OK — will run every day at 6:00 PM.
) else (
    echo       FAILED to create Daily PM task.
)

echo.

:: ── Task 3: At logon + 5 minute delay ────────────────────────────────────
echo  [3/4] Creating task: At logon (5 min delay)...
schtasks /create ^
  /tn "%TASK_FOLDER%\M+ Import - At Logon" ^
  /tr "wscript.exe \"%VBS_RUN%\"" ^
  /sc ONLOGON ^
  /delay 0005:00 ^
  /f
if %errorlevel% equ 0 (
    echo       OK — will run 5 minutes after you log into Windows.
) else (
    echo       FAILED to create Logon task.
)

echo.

:: ── Task 4: WoW Watcher on Logon ─────────────────────────────────────────
echo  [4/4] Creating task: WoW Close Watcher (At Logon)...
schtasks /create ^
  /tn "%TASK_FOLDER%\M+ Import - WoW Watcher" ^
  /tr "wscript.exe \"%WATCHER_VBS%\"" ^
  /sc ONLOGON ^
  /f
if %errorlevel% equ 0 (
    echo       OK — WoW watcher task created.
    echo       Starting watcher process now...
    schtasks /run /tn "%TASK_FOLDER%\M+ Import - WoW Watcher" >nul 2>&1
) else (
    echo       FAILED to create WoW Watcher task.
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
pause
