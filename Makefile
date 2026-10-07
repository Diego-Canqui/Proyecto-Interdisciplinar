.PHONY: up down logs backend frontend help

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: db backend frontend ## Levanta todo (BD + Backend + Frontend)

db: ## Levanta solo PostgreSQL
	docker compose up -d

backend: ## Levanta solo Backend (FastAPI)
	cd backend && source .venv/bin/activate.fish && .venv/bin/uvicorn prestamos_recursos.main:app --reload --app-dir src

frontend: ## Levanta solo Frontend (Vite)
	cd frontend && npm run dev

down: ## Para todo (contenedores + procesos locales)
	docker compose down
	-pkill -f "uvicorn.*prestamos_recursos" 2>/dev/null || true
	-pkill -f "vite" 2>/dev/null || true

logs: ## Logs de PostgreSQL
	docker compose logs -f postgres

restart-db: ## Reinicia BD (borra volúmenes)
	docker compose down -v
	docker compose up -d

install-backend: ## Instala dependencias Python
	cd backend && source .venv/bin/activate.fish && pip install -r requirements.txt

install-frontend: ## Instala dependencias Node
	cd frontend && npm install

install: install-backend install-frontend ## Instala todo