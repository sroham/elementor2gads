.PHONY: install test lint format build check clean

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .
	python -m ruff format --check .

format:
	python -m ruff check --fix .
	python -m ruff format .

build:
	python -m build

check: lint test build
	python -m twine check dist/*

clean:
	python -c "import pathlib, shutil; [shutil.rmtree(path, ignore_errors=True) for path in map(pathlib.Path, ('build', 'dist', '.pytest_cache', '.ruff_cache'))]"
