#!/usr/bin/env python3
"""
Simple BayesElo test using echo to pipe commands
"""

import subprocess
import os
from pathlib import Path

def test_bayeselo_simple():
    """Test BayesElo with a simple echo pipe approach."""
    print("🧪 Simple BayesElo test...")
    
    # Change to the correct directory
    os.chdir(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
    
    # Create a simple command string
    commands = [
        "reset",
        'addplayer "V7P3R"',
        'addplayer "SlowMate"',
        'addresult "V7P3R" "SlowMate" 2',
        'addresult "SlowMate" "V7P3R" 0',
        "elo",
        "mm",
        "exactdist",
        "ratings",
        "x"
    ]
    
    # Join commands with newlines
    command_string = "\n".join(commands)
    
    print("📝 Commands to send:")
    print(command_string)
    print("=" * 50)
    
    try:
        # Use echo to pipe commands to BayesElo
        result = subprocess.run(
            f'echo "{command_string}" | ./utilities/bayeselo.exe',
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("🔍 BayesElo output:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  Stderr:")
            print(result.stderr)
        
        print(f"Exit code: {result.returncode}")
        
    except subprocess.TimeoutExpired:
        print("⚠️  Command timed out")
    except Exception as e:
        print(f"⚠️  Error: {e}")

if __name__ == "__main__":
    test_bayeselo_simple()
