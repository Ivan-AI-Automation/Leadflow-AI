.PHONY: backend frontend test test-cov lint type-check quality docker-up docker-down

PROJECT_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
VENV_BIN := $(PROJECT_ROOT).venv/bin
PYTEST := $(if $(wildcard $(VENV_BIN)/pytest),$(VENV_BIN)/pytest,pytest)
RUFF := $(if $(wildcard $(VENV_BIN)/ruff),$(VENV_BIN)/ruff,ruff)
MYPY := $(if $(wildcard $(VENV_BIN)/mypy),$(VENV_BIN)/mypy,mypy)

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && streamlit run app/main.py --server.port 8501

test:
	cd backend && $(PYTEST)

test-cov:
	cd backend && $(PYTEST) --cov=app --cov-report=term-missing

lint:
	cd backend && $(RUFF) check app tests

type-check:
	cd backend && $(MYPY) app

quality: lint test

docker-up:
	docker compose up --build

docker-down:
	docker compose down
