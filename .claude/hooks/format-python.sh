#!/usr/bin/env bash
# PostToolUse sobre Edit|Write: formatea y autocorrige el fichero Python tocado.
# Corto y silencioso: los hooks se ejecutan constantemente y bloquean el flujo.
set -uo pipefail

payload=$(cat)
path=$(printf '%s' "$payload" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
case "$path" in
  *.py) ;;
  *) exit 0 ;;
esac
[ -f "$path" ] || exit 0

ruff=$([ -x .venv/bin/ruff ] && echo .venv/bin/ruff || command -v ruff) || exit 0
[ -n "$ruff" ] || exit 0

"$ruff" format -q "$path" >/dev/null 2>&1
"$ruff" check --fix -q "$path" >/dev/null 2>&1
exit 0
