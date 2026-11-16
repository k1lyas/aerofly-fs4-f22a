@echo off
rem Windows: double click. Needs Python 3.8+ (https://www.python.org/downloads/ or: winget install Python.Python.3.12)
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY (python --version >nul 2>nul && set PY=python)
if not defined PY (
  echo Python 3 was not found.
  echo Install it from https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^)
  echo or run:  winget install Python.Python.3.12
  echo then start install.bat again.
  pause
  exit /b 1
)
%PY% install.py %*
echo.
pause
