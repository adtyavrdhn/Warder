#!/bin/bash

# Script to set up Docker environment for Warder agent testing
# This script creates the Docker network and builds the agent image

# Exit on error
set -e

echo "Setting up Docker environment for Warder agent testing..."

# Create Docker network if it doesn't exist
NETWORK_NAME="warder_network"
if ! docker network inspect $NETWORK_NAME >/dev/null 2>&1; then
    echo "Creating Docker network: $NETWORK_NAME"
    docker network create $NETWORK_NAME
else
    echo "Docker network $NETWORK_NAME already exists"
fi

# Build agent Docker image
echo "Building agent Docker image..."
cd "$(dirname "$0")/.."
docker build -t warder/agent:latest -f Dockerfile.agent .

echo "Docker environment setup complete!"
echo "Agent image: warder/agent:latest"
echo "Docker network: $NETWORK_NAME"
