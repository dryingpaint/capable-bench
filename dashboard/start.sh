#!/bin/bash

# Start the CapableBench Performance Dashboard

set -e

echo "🚀 Starting CapableBench Performance Dashboard..."
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Must run from dashboard directory"
    echo "   Run: cd dashboard && ./start.sh"
    exit 1
fi

# Check if capablebench module exists in parent
if [ ! -d "../capablebench" ]; then
    echo "❌ Error: capablebench module not found in parent directory"
    echo "   Make sure you're running this from: /path/to/capable-bench/dashboard/"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Start the development server
echo "🌐 Dashboard will be available at: http://localhost:3000"
echo "📊 Data will be loaded from: ../data/tasks, ../data/answers, ../runs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev