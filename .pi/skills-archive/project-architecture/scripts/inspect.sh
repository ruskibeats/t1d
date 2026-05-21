#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

echo "== T1D Companion repo inspect =="
echo "root: $ROOT"
echo

echo "== Python =="
python --version 2>/dev/null || true
if [ -f pyproject.toml ]; then
  echo "pyproject: present"
fi
echo

echo "== Node =="
node --version 2>/dev/null || true
npm --version 2>/dev/null || true
if [ -f package.json ]; then
  echo "root package.json: present"
fi
if [ -f frontend/package.json ]; then
  echo "frontend package.json: present"
fi
echo

echo "== Key files =="
for path in \
  AGENTS.md \
  app/main.py \
  app/agents/coordinator.py \
  app/services/llm_service.py \
  app/services/pattern_service.py \
  app/db/models.py \
  frontend/src/App.tsx \
  .pi/AGENTS.md; do
  if [ -e "$path" ]; then
    echo "ok  $path"
  else
    echo "miss $path"
  fi
done
echo

echo "== Backend module counts =="
find app -type f -name '*.py' | wc -l | awk '{print "python_files=" $1}'
echo

echo "== Frontend module counts =="
if [ -d frontend/src ]; then
  find frontend/src -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.css' \) | wc -l | awk '{print "frontend_files=" $1}'
else
  echo "frontend_files=0"
fi
echo

echo "== Safety keyword scan =="
rg -n "dose|dosing|basal|correction factor|carb ratio|emergency|medical advice|healthcare provider" app .pi docs README.md 2>/dev/null | head -80 || true
echo

echo "== Git status =="
git status --short 2>/dev/null || true
