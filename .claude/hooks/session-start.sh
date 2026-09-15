#!/usr/bin/env bash
# SessionStart: reinyecta el estado minimo del repositorio al arrancar.
# Rama, ultimo commit, estado del inventario y capitulos marcados stale.
set -uo pipefail

echo "## Estado del repositorio"
echo "- Rama: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'desconocida')"
echo "- Ultimo commit: $(git log -1 --oneline 2>/dev/null || echo 'sin commits')"

changed=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
echo "- Ficheros modificados sin commitear: ${changed}"

python=$([ -x .venv/bin/python ] && echo .venv/bin/python || command -v python3) || python=""
if [ -n "$python" ] && [ -f scripts/check_inventory.py ]; then
  if "$python" scripts/check_inventory.py >/dev/null 2>&1; then
    echo "- Inventario (§21): en verde"
  else
    echo "- Inventario (§21): INCOMPLETO — ejecuta 'make inventory' para ver que falta"
  fi
fi

for db in out/*/project.db; do
  [ -e "$db" ] || continue
  project=$(basename "$(dirname "$db")")
  stale=$(sqlite3 "$db" "SELECT group_concat(number) FROM chapter WHERE stale = 1;" 2>/dev/null)
  [ -n "$stale" ] && echo "- Proyecto '${project}': capitulos stale ${stale}"
done

echo "- Antes de cualquier commit: 'make verify' en verde."
exit 0
