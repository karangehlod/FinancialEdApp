#!/bin/bash

# Financial Education App - Frontend Setup Script
# This script sets up the development environment

echo "🚀 Setting up Financial Education App Frontend..."
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed successfully"
echo ""

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local..."
    cp .env.example .env.local
    echo "✅ Created .env.local with default values"
else
    echo "✅ .env.local already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📖 Next steps:"
echo "1. Make sure your backend is running on http://localhost:8000"
echo "2. Run: npm run dev"
echo "3. Open your browser to http://localhost:3000"
echo ""
echo "📚 For more information, see README.md"
