@echo off
REM ====================================================================================================
REM  CeDInt Energy Dashboard (Sprint 4, Task 3) - one-click launcher for Windows
REM
REM  Double-click this file. It works without any setup:
REM    1. uses the folder that contains Sprint4_Task3_UX_Dash (the repository)
REM    2. creates the Python environment .venv if it is missing (Python 3.11+ required)
REM    3. installs the packages the first time (and whenever requirements change)
REM    4. starts the dashboard and opens http://127.0.0.1:8050 in the browser
REM  Close this window (or press Ctrl+C) to stop the dashboard.
REM ====================================================================================================
setlocal EnableDelayedExpansion
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
for %%I in ("%APP_DIR%\..") do set "REPO=%%~fI"
cd /d "%REPO%"
set "URL=http://127.0.0.1:8050"
echo CeDInt Energy Dashboard - folder: %REPO%

REM 1. Python environment
if not exist ".venv\Scripts\python.exe" (
  set "PY="
  for %%V in (3.13 3.12 3.11) do (
    if not defined PY (
      py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
  )
  if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=python"
  )
  if not defined PY (
    echo Python 3.11 or newer is needed: install it from https://www.python.org/downloads/
    echo ^(tick "Add python.exe to PATH" during the installation^) and run this file again.
    pause
    exit /b 1
  )
  echo Creating the Python environment ^(.venv^) ...
  call !PY! -m venv .venv
  if errorlevel 1 (
    echo Could not create .venv.
    pause
    exit /b 1
  )
)
set "VPY=%REPO%\.venv\Scripts\python.exe"

REM 2. packages (installed once; reinstalled only if the requirements file changes)
set "REQ=%APP_DIR%\requirements-live.txt"
set "STAMP=%REPO%\.venv\.cedint_requirements"
set "NEED=1"
if exist "%STAMP%" (
  fc /b "%REQ%" "%STAMP%" >nul 2>&1 && set "NEED=0"
)
if "%NEED%"=="1" (
  echo Installing the packages ^(first time only, a few minutes^) ...
  "%VPY%" -m pip install --upgrade pip >nul
  "%VPY%" -m pip install -r "%REQ%"
  if errorlevel 1 (
    echo Full install failed; installing the basic packages ^(dashboard without the live forecast^) ...
    "%VPY%" -m pip install -r "%APP_DIR%\requirements.txt"
  ) else (
    copy /y "%REQ%" "%STAMP%" >nul
  )
)

REM 3. open the browser as soon as the dashboard answers
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 90;$i++){Start-Sleep 1; try{Invoke-WebRequest -UseBasicParsing '%URL%' -TimeoutSec 2 | Out-Null; Start-Process '%URL%'; break}catch{}}"

REM 4. start
echo Starting the dashboard ... (close this window or press Ctrl+C to stop it)
"%VPY%" "%APP_DIR%\app.py"
pause
