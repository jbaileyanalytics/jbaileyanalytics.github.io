@echo off
setlocal
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8504
) else (
  echo Python environment missing. Follow README.md to install dependencies.
  exit /b 1
)
