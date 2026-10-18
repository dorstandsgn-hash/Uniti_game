@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set /p URL=Вставьте ссылку на Shorts-нарезку и нажмите Enter: 
.venv\Scripts\python -m sf --url "%URL%"
pause
