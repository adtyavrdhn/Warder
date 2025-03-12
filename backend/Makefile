.PHONY: install setup-db run test dev lint format build deploy clean

# Variables
PYTHON = python3
PIP = pip3
DOCKER = docker
KUBECTL = kubectl
COMPOSE = docker-compose

# Default target
all: install

# Install dependencies
install:
	$(PIP) install -r requirements.txt
	cd api_gateway && $(PIP) install -e .
	cd agent_manager && $(PIP) install -e .
	cd document_processor && $(PIP) install -e .

# Set up the database
setup-db:
	cd database && $(PYTHON) scripts/setup_db.py

# Run the services
run:
	$(COMPOSE) up

# Run in development mode
dev:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up

# Run tests
test:
	pytest tests/
	cd api_gateway && pytest tests/
	cd agent_manager && pytest tests/
	cd document_processor && pytest tests/

# Run linters
lint:
	flake8 .
	mypy .
	black --check .

# Format code
format:
	black .
	isort .

# Build Docker images
build:
	$(COMPOSE) build
	cd docker && ./build_all.sh

# Deploy to Kubernetes
deploy:
	cd kubernetes && ./deploy.sh

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
