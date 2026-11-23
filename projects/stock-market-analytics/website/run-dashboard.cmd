@echo off
setlocal
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is required. See the project README for setup.
  pause
  exit /b 1
)
if exist "%~dp0..\results\kaggle-refresh-v841\site\index.html" (
  echo Starting the refreshed dashboard, with data through November 18, 2026.
  set MARKETSCOPE_PORT=8767
  echo Keep this window open while using the dashboard. Press Ctrl+C to stop it.
  node "%~dp0serve.cjs" --candidate --open
  pause
  exit /b
)
echo Starting the original local dashboard.
echo Keep this window open while using the dashboard. Press Ctrl+C to stop it.
node "%~dp0serve.cjs" --open
pause
