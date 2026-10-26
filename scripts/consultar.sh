#!/usr/bin/env bash
# consultar.sh — Utilidad de desarrollo para consultar la base de datos del proyecto.
#
# Uso:
#   ./scripts/consultar.sh 'SELECT * FROM identidad_reputacion.usuario;'   (modo consulta)
#   ./scripts/consultar.sh                                                (modo interactivo)
#
# No lee ni imprime secretos: solo usa POSTGRES_USER y POSTGRES_DB del .env.
# La conexión va por el socket interno del contenedor, así que no hace falta contraseña.

set -euo pipefail

# Funciona lanzado desde cualquier directorio.
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

USUARIO_DEFECTO="prestamos"
BASE_DEFECTO="prestamos_recursos"
SERVICIO="db"
ESPERAS_MAXIMAS=30

# Lee una clave del .env sin hacer `source` (evita romper con JWT_SECRET).
leer_env() {
  local clave="$1" defecto="$2" valor comilla_simple="'" comilla_doble='"'
  valor="$(grep -E "^${clave}=" .env 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  valor="${valor%$'\r'}"
  # Quita comillas envolventes si las hubiera.
  valor="${valor#"$comilla_doble"}"; valor="${valor%"$comilla_doble"}"
  valor="${valor#"$comilla_simple"}"; valor="${valor%"$comilla_simple"}"
  if [ -z "$valor" ]; then
    valor="$defecto"
  fi
  printf '%s' "$valor"
}

mostrar_ayuda() {
  cat <<'FIN'
Uso:
  ./scripts/consultar.sh 'CONSULTA'   Ejecuta una consulta SQL y termina.
  ./scripts/consultar.sh              Abre psql interactivo (search_path ya configurado).

Ejemplos:
  ./scripts/consultar.sh 'SELECT * FROM identidad_reputacion.usuario;'
  ./scripts/consultar.sh '\dt identidad_reputacion.*'

Nota: las tablas las crea el backend al arrancar (make backend); la BD sola no las tiene.
FIN
}

# Corta con error si algo de la infraestructura no está disponible.
error_infra() {
  echo "ERROR: $1" >&2
  exit 1
}

# Levanta la BD si hace falta (silencioso salvo en caso de fallo).
asegurar_db() {
  if ! docker info >/dev/null 2>&1; then
    error_infra "Docker no responde. ¿Está Docker arrancado?"
  fi

  local salida
  if ! salida="$(docker compose up -d "$SERVICIO" 2>&1)"; then
    echo "ERROR: no se pudo levantar el servicio '$SERVICIO' de docker compose." >&2
    printf '%s\n' "$salida" >&2
    exit 1
  fi
}

# Espera a que PostgreSQL acepte conexiones.
esperar_postgres() {
  local USUARIO="$1" BASE="$2" intento
  for intento in $(seq 1 "$ESPERAS_MAXIMAS"); do
    if docker compose exec -T "$SERVICIO" pg_isready -U "$USUARIO" -d "$BASE" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  error_infra "PostgreSQL no aceptó conexiones tras ${ESPERAS_MAXIMAS}s. Revisa 'docker compose logs $SERVICIO'."
}

# ¿Existe ya identidad_reputacion.usuario? (las tablas las crea create_all del backend)
hay_tablas() {
  local USUARIO="$1" BASE="$2" resultado
  resultado="$(docker compose exec -T "$SERVICIO" psql -X -q -t -A -U "$USUARIO" -d "$BASE" \
    -c "SELECT to_regclass('identidad_reputacion.usuario') IS NOT NULL;" 2>/dev/null)" || return 1
  [ "$resultado" = "t" ]
}

avisar_faltan_tablas() {
  cat >&2 <<'FIN'
AVISO: todavía no existen las tablas (falta identidad_reputacion.usuario).
       Las crea el backend al arrancar: ejecuta 'make backend' y vuelve a consultar.
       Nota: los schemas reservas y prestamos siguen vacíos (contextos en stub);
       solo identidad_reputacion y catalogo tienen tablas.
FIN
}

# --- Programa principal -----------------------------------------------------

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  mostrar_ayuda
  exit 0
fi

USUARIO="$(leer_env POSTGRES_USER "$USUARIO_DEFECTO")"
BASE="$(leer_env POSTGRES_DB "$BASE_DEFECTO")"

asegurar_db
esperar_postgres "$USUARIO" "$BASE"

if ! hay_tablas "$USUARIO" "$BASE"; then
  avisar_faltan_tablas
fi

if [ "$#" -gt 0 ]; then
  # Modo consulta: los argumentos se unen y se pasan con -c. Sin -it (no hay TTY).
  consulta="$*"
  docker compose exec -T "$SERVICIO" psql -X -q -U "$USUARIO" -d "$BASE" -P pager=off -c "$consulta"
  exit $?
fi

# Modo interactivo: necesita TTY.
if [ ! -t 0 ]; then
  echo "ERROR: el modo interactivo necesita una terminal (TTY)." >&2
  echo "       Pasa la consulta como argumento, por ejemplo:" >&2
  echo "       ./scripts/consultar.sh 'SELECT * FROM usuario;'" >&2
  exit 1
fi

cat >&2 <<'FIN'
psql interactivo. Ayuda rápida:
  \dn                     lista los schemas
  \dt identidad_reputacion.*   lista las tablas de un schema
  \q                      para salir
FIN

docker compose exec \
  -e "PGOPTIONS=-c search_path=identidad_reputacion,catalogo,reservas,prestamos,public" \
  -it "$SERVICIO" psql -U "$USUARIO" -d "$BASE"
