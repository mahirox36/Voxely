#!/bin/bash
# Voxely Updater — build only, then ask to run

echo "🌀 Pulling latest code..."
git pull origin main || { echo "❌ Git pull failed!"; exit 1; }

echo "🔨 Building Docker images (without starting)..."
docker compose build || { echo "❌ Build failed!"; exit 1; }

echo ""
read -p "✅ Build complete! Do you want to start the containers now? (y/n): " choice

if [[ "$choice" =~ ^[Yy]$ ]]; then
  echo "🚀 Starting containers..."
  docker compose up -d
  echo "✨ Containers are now running!"
else
  echo "🛑 Containers not started. You can start them anytime with:"
  echo "   docker compose up -d"
fi
