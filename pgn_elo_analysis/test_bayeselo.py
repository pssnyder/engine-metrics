"""
Quick BayesElo Test Script
Tests the BayesElo binary with a small sample of recent games.
"""

import subprocess
from pathlib import Path
import tempfile
import os
import time

def test_bayeselo():
    print("🧪 Testing BayesElo with sample data...")
    
    # Sample games data (format: white, black, result)
    # Result: 0=black wins, 1=draw, 2=white wins
    sample_games = [
        ("V7P3R", "SlowMate", "2"),  # V7P3R wins
        ("SlowMate", "C0BR4", "1"),   # Draw
        ("C0BR4", "V7P3R", "0"),     # V7P3R wins (as black)
        ("V7P3R", "SlowMate", "1"),  # Draw
        ("SlowMate", "C0BR4", "2"),   # SlowMate wins
        ("C0BR4", "V7P3R", "2"),     # C0BR4 wins
    ]
    
    # Create BayesElo script with proper termination
    script_lines = [
        "reset",
        'addplayer "V7P3R"',
        'addplayer "SlowMate"',
        'addplayer "C0BR4"',
    ]
    
    # Add results
    for white, black, result in sample_games:
        script_lines.append(f'addresult "{white}" "{black}" {result}')
    
    # Run analysis and save to file
    output_file = "test_ratings.txt"
    script_lines.extend([
        "elo",
        "mm",
        "exactdist",
        f"ratings > {output_file}",
        "p",
        "x"
    ])
    
    script_content = "\n".join(script_lines)
    
    try:
        bayeselo_path = Path("utilities/bayeselo.exe")
        
        if not bayeselo_path.exists():
            print("❌ BayesElo not found at utilities/bayeselo.exe")
            return False
        
        print("📝 Script to send to BayesElo:")
        print(script_content)
        print("\n" + "="*50)
        
        # Write script to temp file
        script_file = "bayeselo_test_script.txt"
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        print(f"💾 Script saved to: {script_file}")
        
        # Clean up any existing output file
        if os.path.exists(output_file):
            os.remove(output_file)
        
        # Use Popen for better control
        process = subprocess.Popen(
            [str(bayeselo_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        # Send input and close stdin
        stdout, stderr = process.communicate(input=script_content, timeout=30)
        
        print("📤 BayesElo Output:")
        print(stdout)
        
        if stderr:
            print("⚠️  Errors:")
            print(stderr)
        
        # Check if output file was created
        if os.path.exists(output_file):
            print(f"✅ Output file created: {output_file}")
            with open(output_file, 'r') as f:
                content = f.read()
                print("📊 Ratings output:")
                print(content)
        else:
            print("⚠️  No output file was created")
        
        print(f"✅ BayesElo test completed with return code: {process.returncode}")
        return process.returncode == 0
        
        print("📤 BayesElo Output:")
        print(stdout)
        
        if stderr:
            print("⚠️  Errors:")
            print(stderr)
        
        # Check if output file was created
        if os.path.exists(output_file):
            print(f"✅ Output file created: {output_file}")
            with open(output_file, 'r') as f:
                content = f.read()
                print("📊 Ratings output:")
                print(content)
        else:
            print("⚠️  No output file was created")
        
        print(f"✅ BayesElo test completed with return code: {process.returncode}")
        return process.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⚠️  BayesElo test timed out")
        try:
            process.kill()
        except:
            pass
        return False
    except Exception as e:
        print(f"❌ Error testing BayesElo: {e}")
        return False
    finally:
        # Clean up temp files
        try:
            if os.path.exists("bayeselo_test_script.txt"):
                os.remove("bayeselo_test_script.txt")
        except:
            pass

if __name__ == "__main__":
    test_bayeselo()
