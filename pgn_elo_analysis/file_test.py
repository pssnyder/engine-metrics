#!/usr/bin/env python3
"""
BayesElo test using file input instead of printf to avoid hanging
"""

import os
import subprocess
from pathlib import Path

def test_bayeselo_with_file():
    """Test BayesElo using file input redirection."""
    print("🧪 Testing BayesElo with file input...")
    
    os.chdir(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
    
    # Create a simple test script
    script_content = """reset
addplayer "V7P3R"
addplayer "SlowMate"
addplayer "C0BR4"
addresult "V7P3R" "SlowMate" 2
addresult "SlowMate" "C0BR4" 1
addresult "C0BR4" "V7P3R" 0
addresult "V7P3R" "SlowMate" 1
addresult "SlowMate" "C0BR4" 2
addresult "C0BR4" "V7P3R" 2
elo
mm
exactdist
ratings > file_test_results.txt
x"""
    
    # Write script to file
    script_file = "test_script.txt"
    with open(script_file, 'w') as f:
        f.write(script_content)
    
    print(f"📝 Script saved to {script_file}")
    print("🚀 Running BayesElo with file input...")
    
    try:
        # Try using file redirection
        bayeselo_path = r"utilities\bayeselo.exe"
        
        # Use < for input redirection
        result = subprocess.run(
            f'{bayeselo_path} < {script_file}',
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"✅ Completed with exit code: {result.returncode}")
        
        if result.stdout:
            print("📤 Stdout:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️  Stderr:")
            print(result.stderr)
        
        # Check for results
        result_files = ["file_test_results.txt", " file_test_results.txt"]
        for result_file in result_files:
            if Path(result_file).exists():
                print(f"📊 Results found in {result_file}:")
                with open(result_file, 'r') as f:
                    print(f.read())
                break
        else:
            print("❌ No results file found")
            
    except subprocess.TimeoutExpired:
        print("⚠️  Timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up
        if Path(script_file).exists():
            Path(script_file).unlink()

if __name__ == "__main__":
    test_bayeselo_with_file()
