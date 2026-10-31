@echo off
rem ---------------------------------------------------------------------
rem  Aircraft Sizing Calculator - launcher
rem  Finds a Python 3 runtime and starts the GUI without a console window.
rem  Pure ASCII on purpose: the batch file stays readable under any code page.
rem ---------------------------------------------------------------------
cd /d "%~dp0"
setlocal enabledelayedexpansion

set "APP=aircraft_sizing_calculator.py"
if not exist "%APP%" (
    echo main script not found: %APP%
    pause
    exit /b 1
)

rem ---- pick a runner: py -3w -> pythonw -> python ----
set "RUN="
py -3w -c "pass" <NUL >nul 2>&1 && set "RUN=py -3w"
if not defined RUN (
    where pythonw >nul 2>&1 && set "RUN=pythonw"
)
if not defined RUN (
    where python >nul 2>&1 && set "RUN=python"
)
if not defined RUN goto :nopy

start "" %RUN% "%APP%"
exit /b 0

:nopy
echo.
echo  [X] Python 3 was not found on this computer.
echo.
echo      Run  install_environment.bat  to install it automatically, or get it
echo      from  https://www.python.org/downloads/windows/  and tick
echo      "Add python.exe to PATH" during the installation.
echo.
pause
exit /b 1
