#!/bin/bash

# Admin Dashboard Startup Script
# Runs on port 8001 on each deployment instance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting Admin Dashboard..."

# Check environment variables
if [ -z "$DEPLOYMENT_ID" ]; then
    echo "⚠️  DEPLOYMENT_ID not set, using 'unknown'"
    export DEPLOYMENT_ID="unknown"
fi

if [ -z "$MASTER_HOST" ]; then
    echo "⚠️  MASTER_HOST not set, using '127.0.0.1'"
    export MASTER_HOST="127.0.0.1"
fi

if [ -z "$MASTER_PORT" ]; then
    echo "⚠️  MASTER_PORT not set, using 8000"
    export MASTER_PORT=8000
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# Run the server
echo "✅ Admin Dashboard ready"
echo "📍 Deployment: $DEPLOYMENT_ID"
echo "🔗 Master: $MASTER_HOST:$MASTER_PORT"
echo "🌐 Listening on http://0.0.0.0:8001"
echo ""

cd "$SCRIPT_DIR"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
