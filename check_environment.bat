@echo off
rem ---------------------------------------------------------------------
rem  Aircraft Sizing Calculator - environment check
rem  Verifies Python / tkinter / program files / the calculation core and
rem  writes the report next to this script. Pure ASCII on purpose.
rem ---------------------------------------------------------------------
setlocal
cd /d "%~dp0"

call :detect
if not defined PYCMD goto :nopy

echo Interpreter: %PYCMD%
echo.
%PYCMD% "%~dp0tools\env_check.py"
echo.
pause
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
