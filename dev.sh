#!/usr/bin/env bash
# dev.sh - levanta BD, Backend, Frontend en background
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

echo "⚛️  Iniciando Frontend (Vite)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n✅ TODO CORRIENDO"
echo "   Backend:  http://localhost:8000/docs"
echo "   Frontend: http://localhost:5173"
echo "   Presiona Ctrl+C para parar todo\n"

wait $BACKEND_PID $FRONTEND_PID