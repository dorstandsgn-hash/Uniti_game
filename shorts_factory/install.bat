@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   Установка Shorts Factory
echo ==========================================
set NEED_RESTART=0

py -3 --version >nul 2>nul
if errorlevel 1 (
  echo [1/3] Устанавливаю Python 3.12...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  set NEED_RESTART=1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo [2/3] Устанавливаю FFmpeg...
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
  set NEED_RESTART=1
)
where deno >nul 2>nul
if errorlevel 1 (
  echo [3/3] Устанавливаю Deno - нужен для скачивания с YouTube...
  winget install -e --id DenoLand.Deno --accept-package-agreements --accept-source-agreements
  set NEED_RESTART=1
)
if "%NEED_RESTART%"=="1" (
  echo.
  echo Программы установлены. ЗАКРОЙТЕ это окно и запустите install.bat ЕЩЁ РАЗ.
  pause
  exit /b
)

if exist .venv (
  .venv\Scripts\python --version >nul 2>nul
  if errorlevel 1 (
    echo Старое окружение Python сломано - пересоздаю...
    rmdir /s /q .venv
  )
)
if not exist .venv (
  echo Создаю окружение Python...
  py -3 -m venv .venv
)
.venv\Scripts\python --version >nul 2>nul
if errorlevel 1 (
  echo ОШИБКА: не удалось создать окружение Python. Переустановите Python 3.12 и запустите install.bat снова.
  pause
  exit /b 1
)
echo Устанавливаю библиотеки (может занять 5-10 минут)...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
echo Устанавливаю библиотеки NVIDIA для ускорения Whisper...
.venv\Scripts\python -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
echo.
echo ==========================================
echo   Готово! Запускайте run.bat
echo   (при первом запуске скачается модель Whisper ~3 ГБ)
echo ==========================================
pause
