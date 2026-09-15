#!/usr/bin/env bash
# PreToolUse sobre Read|Edit|Write.
#
# Sale con codigo 2 si la ruta es un secreto o una base de datos de trabajo. El
# codigo 2 bloquea la llamada ANTES de ejecutarse y devuelve el motivo al modelo.
#
# Esta es la regla mas importante del harness: hace estructuralmente imposible
# que una clave acabe leida o escrita por accidente, en lugar de confiar en que
# el modelo recuerde no hacerlo.
set -uo pipefail

payload=$(cat)
path=$(printf '%s' "$payload" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -z "$path" ] && exit 0

base=$(basename "$path")
case "$base" in
  .env|.env.*)
    echo "BLOQUEADO: '$path' contiene credenciales. Usa .env.example, que solo tiene marcadores." >&2
    exit 2 ;;
esac
case "$path" in
  *.key|*.pem|*id_rsa*)
    echo "BLOQUEADO: '$path' es material criptografico y no debe leerse ni escribirse." >&2
    exit 2 ;;
  out/*.db|out/*/*.db|*/out/*.db|*/out/*/*.db)
    echo "BLOQUEADO: '$path' es una base de datos de trabajo. Consultala con 'novela status' o 'novela continuity'." >&2
    exit 2 ;;
esac
exit 0
