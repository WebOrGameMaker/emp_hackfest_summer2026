#!/usr/bin/env bash
# venv, deps, seed if empty, then serve
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
PORT="${PORT:-8000}"

if [ ! -d "$VENV" ]; then
  echo "==> Creating virtualenv"
  python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

if [ ! -f "$VENV/.deps-installed" ]; then
  echo "==> Installing dependencies"
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -r requirements.txt
  touch "$VENV/.deps-installed"
fi

if [ -f .env ]; then
  echo "==> Loading .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "==> Seeding demo data (no-op if the database already has hazards)"
python -m backend.seed

echo ""
echo "  HazardMap is starting on http://localhost:$PORT"
echo ""

exec python -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT"
