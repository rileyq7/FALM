#!/bin/bash
# Deployment script for FALM system

set -e

echo "=================================================="
echo "FALM Deployment Script"
echo "=================================================="

# Build Docker image
echo "Building Docker image..."
docker build -t falm:latest .

# Run with Docker Compose
echo "Starting services..."
docker-compose up -d

# Wait for services
echo "Waiting for services to start..."
sleep 10

# Check health
echo "Checking health..."
curl -f http://localhost:8000/ || echo "Warning: Health check failed"

echo ""
echo "=================================================="
echo "Deployment complete!"
echo "=================================================="
echo ""
echo "Services:"
echo "- API: http://localhost:8000"
echo "- Docs: http://localhost:8000/docs"
echo "- MongoDB: localhost:27017"
echo ""
echo "Commands:"
echo "- View logs: docker-compose logs -f"
echo "- Stop: docker-compose down"
echo "- Restart: docker-compose restart"
echo ""
