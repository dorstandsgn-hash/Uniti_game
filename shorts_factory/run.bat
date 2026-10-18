@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
.venv\Scripts\python -m pip install -q -U "yt-dlp[default]"
.venv\Scripts\python -m sf %*
pause
