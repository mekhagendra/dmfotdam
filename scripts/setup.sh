#!/bin/bash

# Setup script for Terrorism Detection and Monitoring System

echo "Setting up Terrorism Detection and Monitoring System..."

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating environment file..."
    cp .env.example .env
    echo "Please update .env file with your configuration"
fi

# Setup backend
echo "Setting up Python backend..."
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create data directories
mkdir -p data/uploads data/models data/datasets

# Create .gitkeep files
touch data/uploads/.gitkeep
touch data/models/.gitkeep 
touch data/datasets/.gitkeep

echo "Backend setup complete!"

cd ..

# Setup frontend
echo "Setting up React frontend..."
cd frontend

# Install node dependencies
npm install

echo "Frontend setup complete!"

cd ..

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update backend/.env with your configuration"
echo "2. Start backend:  cd backend && source venv/bin/activate && python main.py"
echo "3. Start frontend: cd frontend && npm start"
echo "For production deploy on Vultr: see scripts/vultr-deploy.sh"