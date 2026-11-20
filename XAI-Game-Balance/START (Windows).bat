@echo off
setlocal
title i-Game Game Balance Tool

if not exist "%~dp0requirements.txt" goto notextracted
cd /d "%~dp0"
set "PYTHONUTF8=1"

if exist ".venv\installed.ok" goto run

echo.
echo First start: setting up the tool. This takes a few minutes and needs an internet connection.
echo.

rem Find Python 3.10 or newer: the "py" launcher first, then "python" on PATH.
rem (The Microsoft Store placeholder "python" fails the check and is skipped.)
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
if not defined PY goto nopython

%PY% preflight.py
if errorlevel 1 goto stop

if exist ".venv" rmdir /s /q ".venv"
%PY% -m venv .venv
if errorlevel 1 goto setupfail
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setupfail
echo ok> ".venv\installed.ok"
echo.
echo Setup complete.

:run
".venv\Scripts\python.exe" launcher.py
echo.
pause
exit /b 0

:nopython
echo Python 3.10 or newer was not found.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH"
echo during installation, then double-click this file again.
echo.
pause
exit /b 1

:notextracted
echo This file is being run from inside the zip.
echo Extract the zip first: right-click it, choose "Extract All...", then open the
echo extracted folder and double-click START (Windows).bat there.
echo.
pause
exit /b 1

:stop
echo.
pause
exit /b 1

:setupfail
echo.
echo Setup failed. Check your internet connection and the messages above, then try again.
if exist ".venv" rmdir /s /q ".venv"
echo.
pause
exit /b 1
