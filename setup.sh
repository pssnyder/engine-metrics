#!/bin/bash

# Engine Metrics Dashboard Startup Script

echo "Starting Engine Metrics Dashboard..."

# Check if we're in the correct directory
if [ ! -f "config/settings.yaml" ]; then
    echo "Error: Please run this script from the engine-metrics root directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Python
if ! command_exists python; then
    if ! command_exists python3; then
        echo "Error: Python is not installed or not in PATH"
        exit 1
    fi
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Check for Node.js (for frontend development)
if ! command_exists node; then
    echo "Warning: Node.js not found. Frontend development server won't be available."
    NODE_AVAILABLE=false
else
    NODE_AVAILABLE=true
fi

# Set up Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Install Node.js dependencies if Node is available
if [ "$NODE_AVAILABLE" = true ]; then
    echo "Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Create database directory if it doesn't exist
mkdir -p database

echo ""
echo "Setup complete!"
echo ""
echo "To start the dashboard:"
echo "1. Backend only: ./start-backend.sh"
if [ "$NODE_AVAILABLE" = true ]; then
    echo "2. Development mode (with live reload): ./start-development.sh"
    echo "3. Full production: ./start-production.sh"
else
    echo "2. Install Node.js to enable frontend development features"
fi
echo ""
echo "The dashboard will be available at: http://localhost:8000"
echo ""
