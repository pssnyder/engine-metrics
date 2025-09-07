#!/usr/bin/env python3
"""
Working BayesElo test that captures ratings output
"""

import subprocess
import os
from pathlib import Path
import time

def test_bayeselo_with_output():
    """Test BayesElo and capture ratings to file."""
    print("🧪 BayesElo test with output capture...")
    
    # Change to the correct directory
    os.chdir(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
    
    # Create commands including output redirection
    commands = [
        "reset",
        'addplayer "V7P3R"',
        'addplayer "SlowMate"',
        'addplayer "C0BR4"',
        'addresult "V7P3R" "SlowMate" 2',
        'addresult "SlowMate" "C0BR4" 1', 
        'addresult "C0BR4" "V7P3R" 0',
        'addresult "V7P3R" "SlowMate" 1',
        'addresult "SlowMate" "C0BR4" 2',
        'addresult "C0BR4" "V7P3R" 2',
        "elo",
        "mm",
        "exactdist",
        "ratings > working_test_ratings.txt",
        "x"
    ]
    
    # Join commands with newlines and escape properly for shell
    command_string = "\\n".join(commands)
    
    print("📝 Commands to send:")
    for cmd in commands:
        print(f"  {cmd}")
    print("=" * 50)
    
    try:
        # Use printf and full path to bayeselo
        bayeselo_path = r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics\utilities\bayeselo.exe"
        shell_command = f'printf "{command_string}\\n" | "{bayeselo_path}"'
        
        result = subprocess.run(
            shell_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("🔍 BayesElo stdout:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  BayesElo stderr:")
            print(result.stderr)
        
        print(f"Exit code: {result.returncode}")
        
        # Check if output file was created
        output_file = Path("working_test_ratings.txt")
        if output_file.exists():
            print("✅ Output file created!")
            print("📊 Contents:")
            print(output_file.read_text())
        else:
            print("❌ No output file created")
        
    except subprocess.TimeoutExpired:
        print("⚠️  Command timed out")
    except Exception as e:
        print(f"⚠️  Error: {e}")

if __name__ == "__main__":
    test_bayeselo_with_output()
