#!/bin/bash

# Exit on error
set -e

# Change to the backend directory
cd "$(dirname "$0")/.."

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Create data directory if it doesn't exist
mkdir -p data/documents

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 -U postgres > /dev/null 2>&1; then
  echo "PostgreSQL is not running. Please start PostgreSQL first."
  exit 1
fi

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
  echo "Redis is not running. Please start Redis first."
  exit 1
fi

# Setup database if it doesn't exist
python database/scripts/setup_db.py

# Run services in separate terminals
echo "Starting API Gateway..."
cd api_gateway && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_GATEWAY_PID=$!

echo "Starting Agent Manager..."
cd ../agent_manager && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
AGENT_MANAGER_PID=$!

echo "Starting Document Processor..."
cd ../document_processor && python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload &
DOCUMENT_PROCESSOR_PID=$!

# Trap to kill all processes on exit
trap "kill $API_GATEWAY_PID $AGENT_MANAGER_PID $DOCUMENT_PROCESSOR_PID" EXIT

echo "All services are running!"
echo "API Gateway: http://localhost:8000"
echo "Agent Manager: http://localhost:8001"
echo "Document Processor: http://localhost:8002"
echo "Press Ctrl+C to stop all services"

# Wait for all processes to finish
wait
