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
echo Ручной режим: свой файл фильма + таймкоды.
set /p FILE=Перетащите сюда файл фильма и нажмите Enter: 
set /p START=Начало (например 01:12:30): 
set /p END=Конец (например 01:13:20): 
set /p MOVIE=Название фильма: 
.venv\Scripts\python -m sf --file %FILE% --start %START% --end %END% --movie "%MOVIE%"
pause
