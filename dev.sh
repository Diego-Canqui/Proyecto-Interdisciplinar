#!/usr/bin/env bash
# dev.sh - Levanta PostgreSQL, Backend, Frontend y carga los datos semilla automáticamente.
# Uso: ./dev.sh  (y Ctrl+C para parar todo)

set -e

cleanup() {
  echo -e "\n🛑 Parando servicios..."
  pkill -f "uvicorn.*prestamos_recursos" 2>/dev/null || true
  pkill -f "vite" 2>/dev/null || true
  docker compose down 2>/dev/null || true
  echo "✅ Todo parado"
  exit 0
}
trap cleanup INT TERM

echo "🐘 Iniciando PostgreSQL..."
docker compose up -d

echo "🐍 Iniciando Backend (FastAPI)..."
cd backend
source .venv/bin/activate
.venv/bin/uvicorn prestamos_recursos.main:app --reload --app-dir src &
BACKEND_PID=$!
cd ..

# Esperar a que FastAPI arranque y cree las tablas para cargar los datos iniciales (seed.sql)
if [ -f "db/seed.sql" ]; then
  echo "⏳ Esperando a que el backend inicialice las tablas..."
  for _ in $(seq 1 20); do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  echo "🌱 Cargando recursos y usuarios iniciales (db/seed.sql)..."
  docker compose exec -T db psql -X -q -U "${POSTGRES_USER:-prestamos}" -d "${POSTGRES_DB:-prestamos_recursos}" < db/seed.sql >/dev/null 2>&1 || true
fi

echo "⚛️  Iniciando Frontend (Vite)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n=== 🚀 TODO CORRIENDO ==="
echo "   PÁGINAS DISPONIBLES:"
echo "   --------------------------------------------------------"
echo "   🌐 App Principal:       http://localhost:5173/"
echo "   🔑 Login:               http://localhost:5173/login"
echo "   📝 Registro:            http://localhost:5173/registro"
echo "   📚 API Docs (Swagger):  http://localhost:8000/docs"
echo ""
echo "   👤 CUENTAS PRECARGADAS PARA PROBAR:"
echo "   --------------------------------------------------------"
echo "   • Admin / Gestor:  admin@example.com       (clave: admin123)"
echo "   • Estudiante:      estudiante@example.com  (clave: estudiante123)"
echo ""
echo "   Presiona Ctrl+C para detener todos los servicios\n"

wait $BACKEND_PID $FRONTEND_PID
