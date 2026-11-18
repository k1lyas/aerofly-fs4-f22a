@echo off
rem Windows: double click. Uses the Python that comes with the package (folder python\: the official Windows
rem embeddable Python from python.org, nothing is installed); else a Python 3.8+ of the computer
cd /d "%~dp0"
set PY=
if exist "%~dp0python\python.exe" set PY="%~dp0python\python.exe"
if not defined PY (where py >nul 2>nul && set PY=py -3)
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
