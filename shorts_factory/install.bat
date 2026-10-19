@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   Установка Shorts Factory
echo ==========================================
set NEED_RESTART=0

rem Нужен именно Python 3.12: для более новых версий нет готовых библиотек
py -3.12 --version >nul 2>nul
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

rem Пересоздаём окружение, если оно сломано или сделано не на Python 3.12
if exist .venv (
  .venv\Scripts\python -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))" >nul 2>nul
  if errorlevel 1 (
    echo Старое окружение Python не подходит - пересоздаю...
    rmdir /s /q .venv
  )
)
if not exist .venv (
  echo Создаю окружение Python 3.12...
  py -3.12 -m venv .venv
)
.venv\Scripts\python --version >nul 2>nul
if errorlevel 1 (
  echo ОШИБКА: не удалось создать окружение Python 3.12.
  pause
  exit /b 1
)

echo Устанавливаю библиотеки (может занять 5-10 минут)...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ОШИБКА при установке библиотек. Пришлите скриншот этого окна.
  pause
  exit /b 1
)
echo Устанавливаю библиотеки NVIDIA для ускорения Whisper...
.venv\Scripts\python -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
echo.
echo Скачиваю модель распознавания речи (~3 ГБ, один раз, не закрывайте окно)...
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
.venv\Scripts\python -c "from faster_whisper import download_model; download_model('large-v3')"
echo.
echo ==========================================
echo   Готово! Запускайте run.bat
echo ==========================================
pause
