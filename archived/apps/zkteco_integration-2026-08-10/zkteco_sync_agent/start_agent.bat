@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
if not exist "config.json" (
  copy config.example.json config.json
  echo Edit config.json with API key/secret, then run again.
  pause
  exit /b 1
)
start "Exacuer ZKTeco Agent" .venv\Scripts\python.exe agent.py --config config.json
echo Agent started.
