@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
.venv\Scripts\python --version >nul 2>nul
if errorlevel 1 (
  echo Окружение Python не найдено или сломано. Сначала запустите install.bat
  pause
  exit /b 1
)
set /p URL=Вставьте ссылку на Shorts-нарезку и нажмите Enter: 
.venv\Scripts\python -m sf --url "%URL%"
pause
