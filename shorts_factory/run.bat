@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
.venv\Scripts\python -c "import yaml, yt_dlp, faster_whisper" >nul 2>nul
if errorlevel 1 (
  echo Библиотеки не установлены. Сначала запустите install.bat
  pause
  exit /b 1
)
.venv\Scripts\python -m pip install -q -U "yt-dlp[default]"
.venv\Scripts\python -m sf %*
pause
