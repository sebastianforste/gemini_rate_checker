.PHONY: lock install check test lint format

lock:
	uv pip compile requirements.in -o requirements.lock

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.lock

lint:
	ruff check .
	black --check .

test:
	pytest -q

check: lint test

format:
	ruff check --fix .
	black .
