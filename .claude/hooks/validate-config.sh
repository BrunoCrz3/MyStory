#!/usr/bin/env bash
# PostToolUse sobre Edit|Write: si se ha tocado la configuracion, validala ya.
# Una clave mal escrita debe fallar de forma ruidosa en el momento, no tres
# comandos despues.
set -uo pipefail

payload=$(cat)
path=$(printf '%s' "$payload" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
case "$path" in
  *novela.yaml|*novela.example.yaml|*config/*.yaml) ;;
  *) exit 0 ;;
esac

python=$([ -x .venv/bin/python ] && echo .venv/bin/python || command -v python3) || exit 0
[ -n "$python" ] || exit 0

if ! output=$("$python" -m novela config validate 2>&1); then
  echo "La configuracion ha quedado invalida tras editar '$path':" >&2
  echo "$output" >&2
  exit 2
fi
exit 0
