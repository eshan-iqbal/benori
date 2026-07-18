#!/bin/bash

echo "🚀 Starting FMCG Intelligence Agent..."

# Trap Ctrl+C (SIGINT) to gracefully kill both servers when stopping the script
trap "echo -e '\n🛑 Stopping all services...'; kill 0; exit" SIGINT SIGTERM

echo "🧹 Cleaning up existing processes..."
# Kill any process using port 8000 (Backend)
BACKEND_PIDS=$(lsof -ti:8000)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "Killing existing backend process on port 8000..."
    kill -9 $BACKEND_PIDS
fi

# Kill any process using port 3000 (Frontend)
FRONTEND_PIDS=$(lsof -ti:3000)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "Killing existing frontend process on port 3000..."
    kill -9 $FRONTEND_PIDS
fi

# Start FastAPI backend in the background
echo "📦 Starting FastAPI Backend (Port 8000)..."
python3 -m uvicorn backend.api:app --reload --port 8000 &
BACKEND_PID=$!

# Give backend a second to start
sleep 2

# Start Next.js frontend in the background
echo "🎨 Starting Next.js Frontend (Port 3000)..."
cd frontend-nextjs && npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================================"
echo "✅ Both servers are running successfully!"
echo "👉 Frontend App: http://localhost:3000"
echo "👉 Backend API:  http://localhost:8000/docs"
echo "========================================================"
echo "Press Ctrl+C to stop both servers."
echo ""

# Wait for background processes to keep the script running
wait
