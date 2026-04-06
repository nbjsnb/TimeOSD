@echo off
setlocal
cd /d "%~dp0"

set "PY_CMD="
if exist ".venv\Scripts\python.exe" (
  set "PY_CMD=.venv\Scripts\python.exe"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [TimeOSD] Python not found.
    echo [TimeOSD] Please install Python 3.10+ first:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
  )
  set "PY_CMD=python"
)

"%PY_CMD%" -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo [TimeOSD] Missing dependency: PySide6.
  choice /C YN /N /M "Install requirements.txt now? [Y/N]: "
  if errorlevel 2 (
    echo [TimeOSD] Dependency installation canceled. Exit.
    exit /b 1
  )

  "%PY_CMD%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [TimeOSD] Dependency installation failed.
    pause
    exit /b 1
  )
)

"%PY_CMD%" app.py

endlocal

