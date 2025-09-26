#!/bin/bash

# Clear any existing Google Application Credentials
unset GOOGLE_APPLICATION_CREDENTIALS

# Set the project ID
export GOOGLE_CLOUD_PROJECT=chess-engine-metrics-agent

# Start the AI service
cd "$(dirname "$0")"
"S:/Maker Stuff/Programming/Chess Engines/Chess Engine Playground/engine-metrics-agent/venv/Scripts/python.exe" app.py