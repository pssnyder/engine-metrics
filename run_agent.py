#!/usr/bin/env python3
"""
V7P3R Engine Metrics Agent - Root Launcher
Run from anywhere in the workspace:

    python run_agent.py                          # interactive terminal chat
    python run_agent.py -q "win rate as white?"  # single query
    python run_agent.py --help                   # all options

This script sets up the Python path and delegates to src/ai/cli.py.
"""

import sys
import os
from pathlib import Path

# Resolve paths
_ROOT = Path(__file__).resolve().parent
_AI_DIR = _ROOT / "engine-metrics-agent" / "src" / "ai"

if not _AI_DIR.exists():
    print(f"Error: could not find src/ai at {_AI_DIR}", file=sys.stderr)
    sys.exit(1)

# Add ai/ to path so imports work
sys.path.insert(0, str(_AI_DIR))

# Load .env from engine-metrics-agent/src/ai/.env if present
from dotenv import load_dotenv
env_file = _AI_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Try workspace root .env
    load_dotenv(_ROOT / ".env")

from cli import main

if __name__ == "__main__":
    main()
