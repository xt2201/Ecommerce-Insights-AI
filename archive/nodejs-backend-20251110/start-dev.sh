#!/bin/bash
# Start backend development server with correct PATH

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$(dirname "$0")"

echo "🚀 Starting Backend Development Server..."
echo "📍 Node: $(which node)"
echo "📦 npm: $(which npm)"
echo ""

npm run dev
