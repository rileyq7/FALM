#!/bin/bash

# FALM Startup Script

echo "Starting FALM Production System..."

# Activate virtual environment
source venv/bin/activate

# Check if MongoDB is running (optional)
if command -v mongod &> /dev/null; then
    if ! pgrep -x "mongod" > /dev/null; then
        echo "Starting MongoDB..."
        mongod --fork --logpath logs/mongodb.log --dbpath data/mongodb > /dev/null 2>&1
    fi
fi

# Start the API server
echo "Starting FALM API Server..."
echo "Access at: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
python falm_production_api.py
