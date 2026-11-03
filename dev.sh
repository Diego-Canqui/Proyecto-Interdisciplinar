#!/usr/bin/env bash
# dev.sh - levanta BD, Backend, Frontend en background
# Uso: ./dev.sh  (y Ctrl+C para parar todo)

set -e

cleanup() {
  echo -e "\nParando servicios..."
  pkill -f "uvicorn.*prestamos_recursos" 2>/dev/null || true
  pkill -f "vite" 2>/dev/null || true
  docker compose down 2>/dev/null || true
  echo "Todo parado"
  exit 0
}
trap cleanup INT TERM

echo "Iniciando PostgreSQL..."
docker compose up -d

echo "Iniciando Backend (FastAPI)..."
cd backend
source .venv/bin/activate
.venv/bin/uvicorn prestamos_recursos.main:app --reload --app-dir src &
BACKEND_PID=$!
cd ..

if [ -f "db/seed.sql" ]; then
  for _ in $(seq 1 20); do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  echo "Cargando datos iniciales (db/seed.sql)..."
  docker compose exec -T db psql -X -q -U "${POSTGRES_USER:-prestamos}" -d "${POSTGRES_DB:-prestamos_recursos}" < db/seed.sql >/dev/null 2>&1 || true
fi

echo "Iniciando Frontend (Vite)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n=== TODO CORRIENDO ==="
echo "   PAGINAS PARA REVISAR (abre en navegador):"
echo "   ------------------------------------------"
echo "   App principal:      http://localhost:5173/"
echo "   Registro:           http://localhost:5173/registro"
echo "   Login:              http://localhost:5173/login"
echo "   API Docs (Swagger): http://localhost:8000/docs"
echo ""
echo "   Cuentas de prueba:"
echo "      Admin / Gestor:  admin@example.com       (clave: admin123)"
echo "      Estudiante:      estudiante@example.com  (clave: estudiante123)"
echo ""
echo "   Presiona Ctrl+C para parar todo\n"

wait $BACKEND_PID $FRONTEND_PID
