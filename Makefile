.PHONY: install demo test run build docker

install:
	python3 -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm ci

demo:
	.venv/bin/python scripts_export_demo.py

test:
	cd backend && ../.venv/bin/pytest -q
	cd frontend && npm run lint && npm run build

run:
	cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000

build:
	cd frontend && npm run build

docker:
	docker compose up --build

