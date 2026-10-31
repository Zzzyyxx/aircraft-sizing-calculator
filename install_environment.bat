@echo off
rem ---------------------------------------------------------------------
rem  Aircraft Sizing Calculator - one-click environment setup
rem  Looks for an existing Python 3, falls back to winget, re-checks, and
rem  can start the calculator once everything passes. Pure ASCII on purpose.
rem ---------------------------------------------------------------------
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Aircraft Sizing Calculator - environment setup
echo ============================================================
echo.

call :detect
if defined PYCMD goto :verify

echo  [ ] Python 3 not found. Trying to install it with winget ...
echo.
where winget >nul 2>&1
if errorlevel 1 goto :manual

winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo  [X] winget could not finish the installation.
    goto :manual
)

call :detect
if not defined PYCMD (
    echo.
    echo  [!] Python was installed, but this window cannot see it yet.
    echo      Please close this window and run this file again.
    echo.
    pause
    exit /b 1
)

:verify
echo.
echo  Interpreter: %PYCMD%
echo.
%PYCMD% "%~dp0tools\env_setup.py"
exit /b %errorlevel%

:manual
echo.
echo  Please install Python 3.12 or newer by hand:
echo    1) open  https://www.python.org/downloads/windows/
echo    2) download "Windows installer (64-bit)"
echo    3) run it and tick  "Add python.exe to PATH"
echo    4) run this file again
echo.
pause
exit /b 1

:detect
set "PYCMD="
py -3 -c "import sys" <NUL >nul 2>&1 && set "PYCMD=py -3"
if not defined PYCMD (
    python -c "import sys" <NUL >nul 2>&1 && set "PYCMD=python"
)
if not defined PYCMD call :detect_paths
exit /b 0

:detect_paths
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if not defined PYCMD if exist %%p set "PYCMD=%%p"
)
exit /b 0
