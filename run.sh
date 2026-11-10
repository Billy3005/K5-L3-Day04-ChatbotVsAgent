#!/usr/bin/env bash
# Chạy bài tập bằng 1 lệnh (Mac / Linux).
#   ./run.sh setup                 cài môi trường (.venv, thư viện, file .env)
#   ./run.sh check                 kiểm tra 3 TODO (không cần API key)
#   ./run.sh ask "câu hỏi"         hỏi agent 1 câu
#   ./run.sh eval [--level edge]   chấm agent trên dataset, xuất report.md
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python

setup() {
  if [ ! -d .venv ]; then
    echo "→ Tạo môi trường .venv"
    python3 -m venv .venv
  fi
  echo "→ Cài thư viện"
  .venv/bin/pip install -q -r requirements.txt
  if [ ! -f .env ]; then
    cp .env.example .env
    echo "→ Đã tạo file .env. Mở file này và điền ANTHROPIC_API_KEY."
  fi
  echo "✓ Xong. Tiếp theo: ./run.sh check"
}

[ "$1" = "setup" ] || [ -x "$PY" ] || setup

case "$1" in
  setup) setup ;;
  check) "$PY" check.py ;;
  ask)   shift; "$PY" agent.py "$@" ;;
  eval)  shift; "$PY" evaluate.py "$@" ;;
  *)
    echo "Cách dùng:"
    echo "  ./run.sh setup                 cài môi trường"
    echo "  ./run.sh check                 kiểm tra 3 TODO (không cần API key)"
    echo "  ./run.sh ask \"câu hỏi\"         hỏi agent 1 câu"
    echo "  ./run.sh eval [--level edge]   chấm agent trên dataset, xuất report.md"
    ;;
esac
