@echo off
cd /d "%~dp0"
if not exist .venv (
  echo ==^> Creating virtual environment
  python -m venv .venv
)
call .venv\Scripts\activate.bat
if not exist .venv\.deps_installed (
  echo ==^> Installing dependencies ^(a few minutes the first time^)
  python -m pip install --upgrade pip -q
  python -m pip install -r requirements.txt
  echo done> .venv\.deps_installed
)
if not exist .env if exist .env.demo (
  echo ==^> No .env found; using bundled demo credentials
  copy .env.demo .env >nul
  echo     Operator ID: ssb.operator   Password: Drishti@BOP04
)
echo ==^> Starting Drishti on http://127.0.0.1:8000
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
