#!/bin/bash

# Exit on error
set -e

echo "Deploying Warder Agentic System Infrastructure to Kubernetes..."

# Create namespace if it doesn't exist
kubectl apply -f namespace.yaml

# Apply secrets
kubectl apply -f secrets.yaml

# Deploy database services
echo "Deploying database services..."
kubectl apply -f database/postgres.yaml
kubectl apply -f database/redis.yaml

# Wait for database to be ready
echo "Waiting for database to be ready..."
kubectl wait --namespace=warder --for=condition=ready pod -l app=postgres --timeout=300s

# Deploy core services
echo "Deploying core services..."
kubectl apply -f document-processor/pvc.yaml
kubectl apply -f document-processor/deployment.yaml
kubectl apply -f document-processor/service.yaml

kubectl apply -f agent-manager/service-account.yaml
kubectl apply -f agent-manager/deployment.yaml
kubectl apply -f agent-manager/service.yaml

kubectl apply -f api-gateway/deployment.yaml
kubectl apply -f api-gateway/service.yaml

# Deploy ingress
echo "Deploying ingress..."
kubectl apply -f ingress/ingress.yaml

echo "Deployment completed successfully!"
echo "API is accessible at: https://warder.example.com/api"
echo "API documentation is accessible at: https://warder.example.com/docs"
