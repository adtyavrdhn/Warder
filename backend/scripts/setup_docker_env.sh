#!/bin/bash

# Script to set up Podman environment for Warder agent testing
# This script creates the Podman network and builds the agent image

# Exit on error
set -e

echo "Setting up Podman environment for Warder agent testing..."

# Create Podman network if it doesn't exist
NETWORK_NAME="warder_network"
if ! podman network inspect $NETWORK_NAME >/dev/null 2>&1; then
    echo "Creating Podman network: $NETWORK_NAME"
    podman network create $NETWORK_NAME
else
    echo "Podman network $NETWORK_NAME already exists"
fi

# Build agent Podman image
echo "Building agent Podman image..."
cd "$(dirname "$0")/.."
podman build -t warder/agent:latest -f Dockerfile.agent .

echo "Podman environment setup complete!"
echo "Agent image: warder/agent:latest"
echo "Podman network: $NETWORK_NAME"
