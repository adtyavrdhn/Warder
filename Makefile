SHELL := /bin/bash
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: all install build test clean venv

all: venv install build test

venv:
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV)

install: venv
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

build:
	@echo "Building project..."
	$(PYTHON) setup.py build

test:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/
	$(PYTHON) -m flake8 src/
	$(PYTHON) -m mypy src/

clean:
	@echo "Cleaning..."
	rm -rf $(VENV)
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
