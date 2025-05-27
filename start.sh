#!/bin/bash

# FastAPI Geoportal App Startup Script

echo "🚀 Starting FastAPI Geoportal App..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt

# Start the FastAPI application
echo "🌐 Starting FastAPI server..."
echo "📱 Open http://localhost:8000 in your browser"
echo "🛑 Press Ctrl+C to stop the server"

cd app && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
