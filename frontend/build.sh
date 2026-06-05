#!/bin/bash

# Build script for production
echo "🏗️  Building Financial Education App Frontend..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

# Build
echo "🔨 Building application..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "✅ Build successful!"
echo "📁 Output: dist/"
echo ""
echo "🚀 To serve the production build:"
echo "npm run preview"
