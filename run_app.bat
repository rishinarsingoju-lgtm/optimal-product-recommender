@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating local virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -m pip show fastapi >nul 2>&1
if errorlevel 1 (
  echo Installing project dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

powershell -NoProfile -Command "try { Invoke-RestMethod -Uri http://127.0.0.1:8000/health -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo CompareIQ is already running at http://127.0.0.1:8000
  goto :eof
)

echo Starting CompareIQ at http://127.0.0.1:8000
echo Press Ctrl+C in this window to stop the server.
".venv\Scripts\python.exe" -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
goto :eof

:error
echo.
echo Setup failed. Check the error above, then run this file again.
exit /b 1
