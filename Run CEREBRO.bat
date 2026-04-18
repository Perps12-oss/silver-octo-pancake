@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m cerebro.v2
) else (
  python -m cerebro.v2
)
pause
