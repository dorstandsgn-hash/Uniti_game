@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
.venv\Scripts\python -c "import yaml, yt_dlp, faster_whisper" >nul 2>nul
if errorlevel 1 (
  echo Библиотеки не установлены. Сначала запустите install.bat
  pause
  exit /b 1
)
set /p URL=Вставьте ссылку на Shorts-нарезку и нажмите Enter: 
.venv\Scripts\python -m sf --url "%URL%"
pause
