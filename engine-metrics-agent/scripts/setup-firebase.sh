#!/bin/bash

# Engine Metrics Agent - Firebase Setup Script
# This script initializes the Firebase project and sets up the development environment

echo "🚀 Setting up Chess Engine Metrics Agent..."

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI not found. Installing..."
    npm install -g firebase-tools
fi

# Check if user is logged in to Firebase
echo "📋 Checking Firebase authentication..."
firebase login --no-localhost

# Initialize Firebase project
echo "🔥 Initializing Firebase project..."
firebase use chess-engine-metrics-agent

# Set up Firestore
echo "💾 Setting up Firestore..."
firebase firestore:delete --all-collections --yes || true

# Deploy Firestore rules and indexes
firebase deploy --only firestore

# Set up Cloud Storage
echo "🗄️ Setting up Cloud Storage..."
firebase deploy --only storage

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd src/backend/functions
npm install
cd ../../..

# Install frontend dependencies
echo "🎨 Installing frontend dependencies..."
cd src/frontend
npm install
cd ../..

# Set up Python environment
echo "🐍 Setting up Python environment..."
python -m venv venv

# Activate virtual environment and install dependencies
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Unix/Linux/macOS
    source venv/bin/activate
fi

pip install -r src/ai/requirements.txt

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Run 'npm run dev' to start the development environment"
echo "2. Upload your PGN/JSON/MD files via the web interface"
echo "3. Start asking AI questions about your chess engines!"
echo ""
echo "💡 Example questions to try:"
echo "  • How has V7P3R improved over time?"
echo "  • Which engine performs best in blitz?"
echo "  • Compare SlowMate vs C0BR4 performance"