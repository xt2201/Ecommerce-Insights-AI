#!/bin/bash

PORT=2024

echo "🔍 Checking port $PORT..."

# Check if port is in use and kill the process
if fuser -k $PORT/tcp > /dev/null 2>&1; then
    echo "✅ Killed existing process on port $PORT"
fi

# Also kill any lingering cloudflared processes to ensure a fresh tunnel
pkill -f cloudflared > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Killed lingering cloudflared processes"
fi

# Wait a moment for the port to be fully released
sleep 2

echo "🚀 Starting LangGraph dev server..."
# Run langgraph with --tunnel and any additional arguments
langgraph dev --tunnel "$@"
