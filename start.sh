#!/bin/bash

echo "🚀 AI Paper Reviewer - Quick Start Script"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env file and add your API keys:"
    echo "   - GOOGLE_API_KEY"
    echo "   - TAVILY_API_KEY"
    echo ""
    read -p "Press Enter after adding your API keys..."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploads reviews

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the app: python app.py"
echo "  3. Open browser: http://localhost:5000"
echo ""
echo "To run now, execute:"
echo "  python app.py"
