#!/bin/bash
# Setup script for FALM system

set -e

echo "=================================================="
echo "FALM Setup Script"
echo "=================================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Create directories
echo "Creating directories..."
mkdir -p logs
mkdir -p data/grants/innovate_uk
mkdir -p data/grants/horizon_europe
mkdir -p data/grants/nihr
mkdir -p data/grants/ukri
mkdir -p data/nlms
mkdir -p data/chroma

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env and add your API keys"
fi

echo ""
echo "=================================================="
echo "Setup complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python main.py"
echo "4. Open http://localhost:8000/docs"
echo ""
