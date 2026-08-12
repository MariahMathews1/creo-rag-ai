PYTHON ?= python3.12

.PHONY: install migrate seed-manual-demo seed-traceability-demo seed-profile-extraction-demo seed-approved-program-demo dev dev-backend dev-frontend test build

install:
	$(PYTHON) -m venv backend/.venv
	backend/.venv/bin/python -m pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload

migrate:
	backend/.venv/bin/alembic -c alembic.ini upgrade head

seed-manual-demo:
	cd backend && .venv/bin/python -m app.scripts.seed_manual_demo

seed-traceability-demo:
	cd backend && .venv/bin/python -m app.scripts.seed_traceability_demo

seed-profile-extraction-demo:
	cd backend && .venv/bin/python -m app.scripts.seed_profile_extraction_demo

seed-approved-program-demo:
	cd backend && .venv/bin/python -m app.scripts.seed_approved_program_demo

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest
	cd frontend && npm run lint && npm run typecheck && npm test

build:
	cd frontend && npm run build
