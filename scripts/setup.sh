#!/usr/bin/env bash
# One-time project setup. Run this once after cloning:  ./scripts/setup.sh
# (Windows: run it from Git Bash.) Safe to run again — it just re-applies settings.
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

echo "==> Setting up this project..."

# 1. Point git at our shared hooks folder (so the docs reminder works for everyone).
if [ -d .git ]; then
  git config core.hooksPath .githooks
  chmod +x .githooks/* 2>/dev/null || true
  echo "    git hooks enabled (.githooks)"
else
  echo "    (!) Not a git repo yet. Clone the repo, then re-run this script."
fi

# 2. Make scripts executable.
chmod +x scripts/*.sh 2>/dev/null || true

# 3. Remind about the environment file and the virtual environment.
if [ ! -f .env ] && [ -f .env.example ]; then
  echo "    (!) No .env found. Run: cp .env.example .env   then fill it in."
fi
if [ ! -d .venv ]; then
  echo "    (!) No .venv found. See docs/setup.md to create it."
fi

echo "==> Done."
echo
echo "Next steps:"
echo "  1. cp .env.example .env   (and fill in values; never commit .env)"
echo "  2. install dependencies   (see docs/setup.md)"
echo "  3. read AGENTS.md         (project rules for humans and AI tools)"
echo "  4. run the tests          (pytest -q)"
