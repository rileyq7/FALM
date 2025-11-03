#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      STARTING FALM FEDERATED MESH SYSTEM                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run: bash scripts/setup.sh"
    exit 1
fi

source venv/bin/activate

echo "🌐 Starting Federated Mesh..."
echo "   Each funding body runs as an autonomous node"
echo ""
echo "📍 Server: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🔍 Node Status: http://localhost:8000/api/nodes"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python src/falm_federated_api.py
