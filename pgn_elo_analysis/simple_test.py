#!/usr/bin/env python3
"""
Simple BayesElo test with just recent games to debug the hanging issue
"""

import os
import subprocess
from pathlib import Path
import chess.pgn
from datetime import datetime, timedelta

def run_simple_bayeselo_test():
    """Run BayesElo on a small subset of recent games."""
    print("🧪 Simple BayesElo test with recent games...")
    
    os.chdir(r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics")
    
    # Get just today's games
    game_records = Path("game_records")
    today_dir = None
    
    for battle_dir in sorted(game_records.iterdir(), reverse=True):
        if battle_dir.is_dir() and "Engine Battle" in battle_dir.name:
            today_dir = battle_dir
            break
    
    if not today_dir:
        print("❌ No recent battle directory found")
        return
    
    print(f"📁 Using: {today_dir}")
    
    # Get first PGN file
    pgn_files = list(today_dir.glob("*.pgn"))
    if not pgn_files:
        print("❌ No PGN files found")
        return
    
    sample_file = pgn_files[0]
    print(f"📄 Processing: {sample_file}")
    
    # Extract just first 50 games
    games = []
    engines = set()
    
    try:
        with open(sample_file, 'r', encoding='utf-8', errors='ignore') as f:
            game_count = 0
            while game_count < 50:
                try:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    
                    white = game.headers.get('White', '').strip()
                    black = game.headers.get('Black', '').strip()
                    result = game.headers.get('Result', '')
                    
                    if not white or not black or not result:
                        continue
                    
                    # Normalize engine names
                    white = white.replace('_', ' ').replace('.', ' ')
                    black = black.replace('_', ' ').replace('.', ' ')
                    
                    engines.add(white)
                    engines.add(black)
                    
                    # Convert result
                    if result == '1-0':
                        bayeselo_result = '2'
                    elif result == '0-1':
                        bayeselo_result = '0'
                    elif result == '1/2-1/2':
                        bayeselo_result = '1'
                    else:
                        continue
                    
                    games.append((white, black, bayeselo_result))
                    game_count += 1
                    
                except Exception as e:
                    continue
                    
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    print(f"📊 Extracted {len(games)} games with {len(engines)} engines")
    print(f"🏁 Engines: {', '.join(sorted(engines))}")
    
    # Create BayesElo script
    script_lines = ["reset"]
    
    # Add players
    for engine in sorted(engines):
        script_lines.append(f'addplayer "{engine}"')
    
    # Add results
    for white, black, result in games:
        script_lines.append(f'addresult "{white}" "{black}" {result}')
    
    # Add analysis commands
    script_lines.extend([
        "elo",
        "mm", 
        "exactdist",
        "ratings > simple_test_results.txt",
        "x"
    ])
    
    script_content = "\n".join(script_lines)
    command_string = script_content.replace('\n', '\\n')
    
    print(f"📝 Script has {len(script_lines)} lines")
    print("🚀 Running BayesElo...")
    
    try:
        bayeselo_path = r"s:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics\utilities\bayeselo.exe"
        shell_command = f'printf "{command_string}\\n" | "{bayeselo_path}"'
        
        # Run with shorter timeout
        result = subprocess.run(
            shell_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"✅ BayesElo completed with exit code: {result.returncode}")
        
        if result.stdout:
            print("📤 Stdout (last 500 chars):")
            print(result.stdout[-500:])
        
        if result.stderr:
            print("⚠️  Stderr:")
            print(result.stderr)
        
        # Check for results file
        result_files = ["simple_test_results.txt", " simple_test_results.txt"]
        for result_file in result_files:
            if Path(result_file).exists():
                print(f"📊 Results in {result_file}:")
                with open(result_file, 'r') as f:
                    print(f.read())
                break
        else:
            print("❌ No results file found")
            
    except subprocess.TimeoutExpired:
        print("⚠️  BayesElo timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_simple_bayeselo_test()
