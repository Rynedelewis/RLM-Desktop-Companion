@echo off
chcp 65001 >nul
echo RaidLootMatrix Mythic+ EP Import
echo ──────────────────────────────────────────────
echo Fetching last reset AND current reset...
echo.

REM Check if requests is installed, install if not
python -c "import requests" 2>nul
if errorlevel 1 (
    echo Installing required library (requests)...
    pip install requests
    echo.
)

REM Default: fetch both last week and current week.
REM To override: drag raidlootmatrix_mplus.py onto this bat, or run:
REM   python raidlootmatrix_mplus.py --week last
REM   python raidlootmatrix_mplus.py --week current
REM   python raidlootmatrix_mplus.py --week both --dry-run

if "%~1"=="" (
    python "%~dp0raidlootmatrix_mplus.py" --week both
) else (
    python "%~dp0raidlootmatrix_mplus.py" %*
)

echo.
pause
