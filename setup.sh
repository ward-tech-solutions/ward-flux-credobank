#!/bin/bash

echo "🚀 Network Monitoring Dashboard - Setup Script"
echo "=============================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+."
    echo "   Install via: brew install node"
    exit 1
fi

echo "✓ Node.js found: $(node --version)"
echo "✓ npm found: $(npm --version)"
echo ""

# Create virtual environment
echo "📦 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo ""
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Python dependencies installed"

# Install frontend dependencies
echo ""
echo "📦 Installing React dependencies (this may take 2-3 minutes)..."
cd frontend
npm install
echo "✓ Frontend dependencies installed"

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 To start development:"
echo ""
echo "   Terminal 1 (Backend):"
echo "   $ cd \"$(pwd)\""
echo "   $ source venv/bin/activate"
echo "   $ python main.py"
echo ""
echo "   Terminal 2 (Frontend):"
echo "   $ cd \"$(pwd)/frontend\""
echo "   $ npm run dev"
echo ""
echo "Then open: http://localhost:3000"
echo ""
echo "📖 Read MODERNIZATION_GUIDE.md for more details"
