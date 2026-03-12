#!/bin/bash
# Mission Control Master Dashboard startup script

set -e

echo "🎛️  Mission Control Master - Startup"
echo "===================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt

# Register deployments (if config exists)
if [ -f "deployments.json" ]; then
    echo "📡 Registering deployments..."
    python3 init_deployments.py
fi

# Start the server
echo ""
echo "🚀 Starting Mission Control Master on port 8000..."
echo "📊 Dashboard: http://localhost:8000"
echo "📡 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
