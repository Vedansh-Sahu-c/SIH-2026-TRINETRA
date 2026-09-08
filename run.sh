#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "==> Creating virtual environment"
  python3 -m venv .venv
fi
source .venv/bin/activate
if [ ! -f .venv/.deps_installed ]; then
  echo "==> Installing dependencies (a few minutes the first time)"
  pip install --upgrade pip -q
  pip install -r requirements.txt
  touch .venv/.deps_installed
fi
if [ ! -f .env ] && [ -f .env.demo ]; then
  echo "==> No .env found; using bundled demo credentials (.env.demo)"
  cp .env.demo .env
  echo "    Operator ID: ssb.operator   Password: Drishti@BOP04"
fi
echo "==> Starting Drishti on http://127.0.0.1:8000"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
