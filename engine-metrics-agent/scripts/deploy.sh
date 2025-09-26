#!/bin/bash

# Engine Metrics Agent - Deployment Script
# Deploys the complete application to Firebase

echo "🚀 Deploying Chess Engine Metrics Agent..."

# Build frontend
echo "🎨 Building frontend..."
cd src/frontend
npm run build
cd ../..

# Deploy to Firebase
echo "🔥 Deploying to Firebase..."
firebase deploy

echo "✅ Deployment complete!"
echo ""
echo "🌐 Your app is now live at:"
echo "https://chess-engine-metrics-agent.web.app"
echo ""
echo "📊 Monitor your deployment:"
echo "• Firebase Console: https://console.firebase.google.com/project/chess-engine-metrics-agent"
echo "• Functions Logs: firebase functions:log"
echo "• Hosting Logs: firebase hosting:channel:open"