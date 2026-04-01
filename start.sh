#!/bin/bash

# Smart Traffic Control System - Startup Script
# For Unix/Linux/macOS

echo "🚦 Starting Smart Traffic Control System..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 is not installed!"
    echo "   Please install Python 3.9 or higher"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if [ ! -f "venv/installed" ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    touch venv/installed
else
    echo "✅ Dependencies already installed"
fi

echo ""
echo "🚀 Launching system..."
echo ""

# Run the system
python main.py

# Deactivate on exit
deactivate
