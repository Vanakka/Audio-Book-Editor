@echo off
setlocal
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\ffprobe.exe" (
    set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
    exit /b
)
py -3.12 main.py
