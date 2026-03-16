#!/bin/bash

# Development start script for TDM System

echo "Starting Terrorism Detection and Monitoring System in development mode..."

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $1 is already in use"
        return 1
    else
        return 0
    fi
}

# Check if required ports are available
echo "Checking port availability..."
check_port 8000 || (echo "Backend port 8000 is in use. Please stop the service or change the port." && exit 1)
check_port 3000 || (echo "Frontend port 3000 is in use. Please stop the service or change the port." && exit 1)

# Start backend in background
echo "Starting Python backend..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Start frontend
echo "Starting React frontend..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo "System started successfully!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/api/docs"
echo ""
echo "To stop the system, run: kill $BACKEND_PID $FRONTEND_PID"

# Keep script running
wait