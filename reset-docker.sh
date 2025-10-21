#!/bin/bash

echo "🔄 Resetting Docker environment..."

# Stop and remove containers
echo "Stopping containers..."
docker-compose down

# Remove volumes to clear database
echo "Removing volumes..."
docker-compose down -v

# Remove any orphaned containers
echo "Removing orphaned containers..."
docker-compose down --remove-orphans

# Clean up any dangling images
echo "Cleaning up dangling images..."
docker image prune -f

# Rebuild and start
echo "Rebuilding and starting containers..."
docker-compose up --build

echo "✅ Docker environment reset complete!"
