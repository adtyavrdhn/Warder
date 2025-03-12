#!/bin/bash

# Exit on error
set -e

# Build API Gateway image
echo "Building API Gateway image..."
docker build -t warder/api-gateway:latest -f api_gateway/Dockerfile ../api_gateway

# Build Agent Manager image
echo "Building Agent Manager image..."
docker build -t warder/agent-manager:latest -f agent_manager/Dockerfile ../agent_manager

# Build Agent Manager Worker image
echo "Building Agent Manager Worker image..."
docker build -t warder/agent-manager-worker:latest -f agent_manager/Dockerfile.worker ../agent_manager

# Build Document Processor image
echo "Building Document Processor image..."
docker build -t warder/document-processor:latest -f document_processor/Dockerfile ../document_processor

# Build development images if requested
if [ "$1" == "--with-dev" ]; then
    echo "Building development images..."
    docker build -t warder/api-gateway:dev -f api_gateway/Dockerfile.dev ../api_gateway
    docker build -t warder/agent-manager:dev -f agent_manager/Dockerfile.dev ../agent_manager
    docker build -t warder/document-processor:dev -f document_processor/Dockerfile.dev ../document_processor
fi

echo "All images built successfully!"
