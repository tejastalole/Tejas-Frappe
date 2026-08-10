@echo off
taskkill /FI "WINDOWTITLE eq Exacuer ZKTeco Agent*" /T /F >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
  echo Check PID %%a manually if agent still running.
)
echo Stop signal sent.
